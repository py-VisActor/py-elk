# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P21A model/coordinate source closure.
"""Concrete hierarchy segments and original native identity-container hosting.

The small multimap adapter reuses reviewed native bucket collections. It is not
a copy or implementation of the generic Guava collection runtime.
"""
from dataclasses import dataclass

from ..disco import _IdentityMap
from ..radial import IdentitySet
from .graph import LPort
from .graph_configurator import _graph_of


class IdentityMultimap:
    def __init__(self, owner):
        self.owner = owner
        self.map = _IdentityMap(owner)
        self.total_size = 0

    def put(self, key, value):
        values = self.map.get(key)
        if values is None:
            values = IdentitySet(self.owner)
            values.add(value)
            self.total_size += 1
            self.map.put(key, values)
            return True
        before = len(values.values())
        values.add(value)
        changed = len(values.values()) != before
        if changed:
            self.total_size += 1
        return changed

    def keys(self):
        return self.map.keys.values()

    def values_for(self, key):
        values = self.map.get(key)
        # Actual missing get creates an empty view but does not add the key.
        return [] if values is None else values.values()


@dataclass(eq=False)
class CrossHierarchyEdge:
    new_edge: object
    graph: object
    type: str

    @staticmethod
    def _actual(port):
        if port.owner.type == 'EXTERNAL_PORT':
            origin = port.owner.properties.get('ORIGIN')
            if origin is not None and not isinstance(origin, LPort):
                raise TypeError('Actual external-port ORIGIN must be an LPort or null')
            return origin
        return port

    def get_actual_source(self):
        return self._actual(self.new_edge.source)

    def get_actual_target(self):
        return self._actual(self.new_edge.target)


def hierarchy_level(nested, top):
    current = nested
    level = 0
    while True:
        if current is top:
            return level
        node = getattr(current, 'parent_node', None)
        if node is None:
            raise ValueError('Top-level graph is not an ancestor')
        current = _graph_of(node)
        level += 1


class CrossHierarchyEdgeComparator:
    def __init__(self, graph):
        self.graph = graph

    def compare(self, first, second):
        if first.type == 'OUTPUT' and second.type == 'INPUT':
            return -1
        if first.type == 'INPUT' and second.type == 'OUTPUT':
            return 1
        first_level = hierarchy_level(first.graph, self.graph)
        second_level = hierarchy_level(second.graph, self.graph)
        return second_level - first_level if first.type == 'OUTPUT' else first_level - second_level


def change_coordinate_system(point, old, new):
    if old is new:
        return
    graph = old
    while True:
        point.x += graph.offset.x
        point.y += graph.offset.y
        node = getattr(graph, 'parent_node', None)
        if node is not None:
            point.x += graph.padding.left
            point.y += graph.padding.top
            point.x += node.pos.x
            point.y += node.pos.y
            graph = _graph_of(node)
        else:
            break
    graph = new
    while True:
        point.x -= graph.offset.x
        point.y -= graph.offset.y
        node = getattr(graph, 'parent_node', None)
        if node is not None:
            point.x -= graph.padding.left
            point.y -= graph.padding.top
            point.x -= node.pos.x
            point.y -= node.pos.y
            graph = _graph_of(node)
        else:
            break
