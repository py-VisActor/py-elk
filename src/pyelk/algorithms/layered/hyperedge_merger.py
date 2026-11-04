# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P07B in references/e13-kernel-sources.json.
# Standalone processor; crossing/provider scheduling remains separate.
"""Actual hyperedge component IDs and adjacent LONG_EDGE dummy merging."""
from dataclasses import dataclass
from .graph import set_source, set_target

@dataclass(frozen=True)
class MergeState:
    allow_merge: bool
    same_source: bool
    same_target: bool

def check_merge_allowed(current, previous):
    a, b = (current.properties, previous.properties)
    current_labels = a.get('LONG_EDGE_HAS_LABEL_DUMMIES', False)
    previous_labels = b.get('LONG_EDGE_HAS_LABEL_DUMMIES', False)
    source = a.get('LONG_EDGE_SOURCE')
    target = a.get('LONG_EDGE_TARGET')
    same_source = source is not None and source is b.get('LONG_EDGE_SOURCE')
    same_target = target is not None and target is b.get('LONG_EDGE_TARGET')
    if not current_labels and (not previous_labels):
        return MergeState(current.ports[0].id == previous.ports[0].id, same_source, same_target)
    source_allowed = (not current_labels or a.get('LONG_EDGE_BEFORE_LABEL_DUMMY', False)) and (not previous_labels or b.get('LONG_EDGE_BEFORE_LABEL_DUMMY', False))
    target_allowed = (not current_labels or not a.get('LONG_EDGE_BEFORE_LABEL_DUMMY', False)) and (not previous_labels or not b.get('LONG_EDGE_BEFORE_LABEL_DUMMY', False))
    return MergeState(same_source and source_allowed or (same_target and target_allowed), same_source, same_target)

def _neighbors(port):
    for edge in port.incoming_edges:
        yield edge.source
    for edge in port.outgoing_edges:
        yield edge.target
    if port.owner.type == 'LONG_EDGE':
        for other in port.owner.ports:
            if other is not port:
                yield other

def _dfs(port, index):
    port.id = index
    stack = [iter(_neighbors(port))]
    while stack:
        try:
            other = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        if other.id == -1:
            other.id = index
            stack.append(iter(_neighbors(other)))

def identify_hyperedges(graph):
    ports = [port for layer in graph.layers for node in layer.nodes for port in node.ports]
    for port in ports:
        port.id = -1
    index = 0
    for port in ports:
        if port.id == -1:
            _dfs(port, index)
            index += 1

def merge_nodes(source, target, keep_source, keep_target):
    incoming = next((port for port in target.ports if port.side == 'WEST'))
    outgoing = next((port for port in target.ports if port.side == 'EAST'))
    for port in source.ports:
        while port.incoming_edges:
            set_target(port.incoming_edges[0], incoming)
        while port.outgoing_edges:
            set_source(port.outgoing_edges[0], outgoing)
    if not keep_source:
        target.properties.pop('LONG_EDGE_SOURCE', None)
    if not keep_target:
        target.properties.pop('LONG_EDGE_TARGET', None)

def hyperedge_dummy_merger(graph):
    identify_hyperedges(graph)
    for layer in graph.layers:
        previous = None
        index = 0
        while index < len(layer.nodes):
            current = layer.nodes[index]
            if current.type == 'LONG_EDGE' and previous is not None and (previous.type == 'LONG_EDGE'):
                state = check_merge_allowed(current, previous)
                if state.allow_merge:
                    merge_nodes(current, previous, state.same_source, state.same_target)
                    layer.nodes.pop(index)
                    continue
            previous = current
            index += 1
