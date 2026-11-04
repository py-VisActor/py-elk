# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P12A in references/e13-kernel-sources.json.
# Existing original native JS-min/Integer-identity adapters reused unchanged.
# Native map supports identity lookup/value only, not generic HashMap iteration.
"""Actual long-edge target chain and memoized model-order minimum producer."""
from .integer_box_tokens import value_of_integer_box
from .port_distribution import _minimum


def _first_outgoing_edge(node):
    for port in node.ports:
        for edge in port.outgoing_edges:
            return edge
    return None


def get_target_node(port):
    edge = port.outgoing_edges[0]
    while True:
        node = edge.target.owner
        if 'LONG_EDGE_TARGET' in node.properties:
            return node.properties['LONG_EDGE_TARGET'].owner
        if node.type == 'NORMAL':
            return node
        edge = _first_outgoing_edge(node)
        if edge is None:
            return None


def _update_target_model_order(targets, port):
    target = get_target_node(port)
    if target is None:
        port.properties.pop('LONG_EDGE_TARGET_NODE', None)
    else:
        port.properties['LONG_EDGE_TARGET_NODE'] = target
    if target is not None:
        previous = 2147483647
        if target in targets:
            previous = targets[target].value
        edge = port.outgoing_edges[0]
        if not edge.properties.get('REVERSED', False):
            targets[target] = value_of_integer_box(_minimum(edge.properties['MODEL_ORDER'], previous))


def long_edge_target_node_preprocessing(node):
    targets = {}
    if 'TARGET_NODE_MODEL_ORDER' in node.properties:
        return node.properties['TARGET_NODE_MODEL_ORDER']
    for port in node.ports:
        if port.outgoing_edges:
            _update_target_model_order(targets, port)
    node.properties['TARGET_NODE_MODEL_ORDER'] = targets
    return targets
