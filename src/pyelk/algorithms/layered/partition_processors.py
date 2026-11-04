# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 Partition pre/mid/post 41054-41275.
"""Actual partition reachability reversal and temporary complete connections."""
from collections import deque

from ...execution.diagnostics import BasicProgressMonitor
from ..radial import IdentitySet
from .graph import LEdge, LPort, set_port_owner, set_source, set_target
from .native_properties import CanonicalPropertyMap
from .ports import set_side
from .property_access import read_layered_scalar
from .cycles_general import reverse_edge
from .utility_processors import _set_integer


def _partition(node):
    return read_layered_scalar(node, 'PARTITIONING_PARTITION', 'PARTITIONING_PARTITION')


def _outgoing(node):
    for port in node.ports:
        yield from port.outgoing_edges


def must_be_reversed(edge, partitioned_nodes, graph):
    if 'PARTITIONING_PARTITION' in edge.target.owner.properties:
        return _partition(edge.source.owner) > _partition(edge.target.owner)
    source_partition = _partition(edge.source.owner)
    lower = [node for node in partitioned_nodes if _partition(node) < source_partition]
    queue = deque([edge.source.owner])
    visited = IdentitySet(graph)
    visited.add(edge.source.owner)
    while queue:
        current = queue.popleft()
        if any(node is current for node in lower):
            return True
        for outgoing in _outgoing(current):
            target = outgoing.target.owner
            if not visited.contains(target):
                visited.add(target)
                queue.append(target)
    return False


def partition_preprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Partition preprocessing', 1)
    partitioned = [node for node in graph.layerless_nodes
                   if 'PARTITIONING_PARTITION' in node.properties]
    edges = [edge for node in graph.layerless_nodes
             if 'PARTITIONING_PARTITION' in node.properties
             for edge in _outgoing(node) if must_be_reversed(edge, partitioned, graph)]
    for edge in edges:
        reverse_edge(edge, True)
        priority = 1000
        if 'PRIORITY_DIRECTION' in edge.properties:
            priority += read_layered_scalar(edge, 'PRIORITY_DIRECTION', 'PRIORITY_DIRECTION_0')
        _set_integer(edge, 'PRIORITY_DIRECTION', priority)
    monitor.done()


def _dummy_port(node, side):
    port = LPort(properties=CanonicalPropertyMap())
    port.integer_box_identities = port.properties.integer_boxes
    set_port_owner(port, node)
    set_side(port, side)
    port.properties['PARTITION_DUMMY'] = True
    return port


def connect_nodes(first, second):
    for node in first:
        source = _dummy_port(node, 'EAST')
        for other in second:
            target = _dummy_port(other, 'WEST')
            edge = LEdge(properties=CanonicalPropertyMap())
            edge.integer_box_identities = edge.properties.integer_boxes
            edge.properties['PARTITION_DUMMY'] = True
            set_source(edge, source)
            set_target(edge, target)


def partition_midprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Partition midprocessing', 1)
    groups = {}
    for node in graph.layerless_nodes:
        if 'PARTITIONING_PARTITION' in node.properties:
            key = _partition(node)
            if key not in groups:
                groups[key] = IdentitySet(graph)
            groups[key].add(node)
    if not groups:
        # Source early return deliberately does not call monitor.done().
        return
    keys = sorted(groups)
    for first, second in zip(keys, keys[1:]):
        connect_nodes(groups[first].values(), groups[second].values())
    monitor.done()


def partition_postprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Partition postprocessing', 1)
    for layer in graph.layers:
        for node in layer.nodes:
            index = 0
            while index < len(node.ports):
                port = node.ports[index]
                index += 1
                value = port.properties.get('PARTITION_DUMMY')
                if value is None:
                    value = False
                if type(value) is not bool:
                    raise TypeError('Actual PARTITION_DUMMY Boolean required')
                if value:
                    # Source removes the list entry without detaching owner or
                    # edge endpoints; the temporary graph stays externally held.
                    node.ports.pop(index - 1)
                    index -= 1
    monitor.done()
