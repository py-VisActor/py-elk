# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Components P12A/P12B/P12C in references/e13-kernel-sources.json.
"""Real source pair-cost consumers of stateful model-order comparators."""
from .model_order_nodes import ModelOrderNodeComparator
from .model_order_ports import ModelOrderPortComparator
from .model_order_targets import long_edge_target_node_preprocessing


def count_model_order_node_changes(graph, layers, strategy):
    previous = -1
    wrong = 0.0
    for layer in layers:
        comparator = ModelOrderNodeComparator(graph, layers[0] if previous == -1 else layers[previous], strategy, 'EQUAL')
        for first in range(len(layer)):
            for second in range(first + 1, len(layer)):
                if 'MODEL_ORDER' in layer[first].properties and 'MODEL_ORDER' in layer[second].properties and comparator.compare(layer[first], layer[second]) > 0:
                    wrong += 1.0
        previous += 1
    return wrong


def count_model_order_port_changes(graph, layers):
    previous = -1
    wrong = 0.0
    for layer in layers:
        for node in layer:
            owner_graph = node.layer.graph if node.graph is None and node.layer is not None else node.graph
            strategy = owner_graph.properties.get('CONSIDER_MODEL_ORDER_STRATEGY', 'NONE')
            targets = long_edge_target_node_preprocessing(node)
            port_model_order = owner_graph.properties.get('CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER', False)
            comparator = ModelOrderPortComparator(graph, layers[0] if previous == -1 else layers[previous], strategy, targets, port_model_order)
            for first in range(len(node.ports)):
                for second in range(first + 1, len(node.ports)):
                    if comparator.compare(node.ports[first], node.ports[second]) > 0:
                        wrong += 1.0
        previous += 1
    return wrong
