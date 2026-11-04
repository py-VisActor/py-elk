# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P15B in references/e13-kernel-sources.json.
# Existing Apache-noticed GWT comparator sort called unchanged.
"""Actual two-pass SortByInputModel phase and eager source diagnostic text."""
from .diagnostic_strings import node_text, port_list_text, layer_text
from .model_order_nodes import ModelOrderNodeComparator
from .model_order_ports import ModelOrderPortComparator
from .model_order_targets import long_edge_target_node_preprocessing
from .ports import _source_sort
from .property_access import read_layered_scalar


def insertion_sort(layer, comparator):
    for index in range(1, len(layer)):
        temporary = layer[index]
        target = index
        while target > 0 and comparator.compare(layer[target - 1], temporary) > 0:
            layer[target] = layer[target - 1]
            target -= 1
        layer[target] = temporary
    comparator.bigger_than = {}
    comparator.smaller_than = {}


def _strategy(graph):
    return read_layered_scalar(graph, 'CONSIDER_MODEL_ORDER_STRATEGY', 'CONSIDER_MODEL_ORDER_STRATEGY_0')


def _node_comparator(graph, previous, before_ports):
    strategy = _strategy(graph)
    long_edge_strategy = read_layered_scalar(graph, 'CONSIDER_MODEL_ORDER_LONG_EDGE_STRATEGY', 'CONSIDER_MODEL_ORDER_LONG_EDGE_STRATEGY_0')
    read_layered_scalar(graph, 'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY', 'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY_0')
    return ModelOrderNodeComparator.from_layer(graph, previous, strategy, long_edge_strategy, before_ports)


def sort_by_input_model(graph, monitor, *, state=None):
    monitor.begin('Sort By Input Model ' + _strategy(graph), 1)
    layer_index = 0
    for layer in graph.layers:
        layer.id = layer_index
        previous = graph.layers[0 if layer_index == 0 else layer_index - 1]
        comparator = _node_comparator(graph, previous, True)
        insertion_sort(layer.nodes, comparator)
        for node in layer.nodes:
            if read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0') != 'FIXED_ORDER' and read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0') != 'FIXED_POS':
                strategy = _strategy(graph)
                targets = long_edge_target_node_preprocessing(node)
                port_model_order = read_layered_scalar(graph, 'CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER', 'CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER_0')
                comparator = ModelOrderPortComparator.from_layer(graph, previous, strategy, targets, port_model_order)
                _source_sort(node.ports, comparator.compare)
                monitor.log('Node ' + node_text(node, state) + ' ports: ' + port_list_text(node.ports, state))
        comparator = _node_comparator(graph, previous, False)
        insertion_sort(layer.nodes, comparator)
        monitor.log('Layer ' + str(layer_index) + ': ' + layer_text(layer, state))
        layer_index += 1
    monitor.done()


class SortByInputModelProcessor:
    def process(self, graph, monitor):
        sort_by_input_model(graph, monitor, state=getattr(graph, '_source_session', None))
