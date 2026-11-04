# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Stress S01-S07: fixed elkjs 0.12.1 worker, EPL-2.0 OR GPL-3.0-or-later.
# PriorityQueue S08: Copyright 2008 Google Inc., Apache-2.0; narrow emulation
# support port, not a claim of the exact external GWT build identity.
# Worker SHA256 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Native ordered Stress majorization with the real Force initialization.

The mutable comparator queue, Gauss-Seidel update order and original
post-increment convergence boundary are intentional source behavior.
"""
from __future__ import annotations

from .force import import_graph, apply_layout, split_components, recombine_components
from .fixed import _div
from .layered.graph import Vec2
from .layered.components import _double_compare
import math


class _PriorityQueue:
    """S08 actual comparator heap; equal priorities have no stable counter."""
    def __init__(self, compare):
        self.heap = []
        self.compare = compare

    def offer(self, value):
        node = len(self.heap)
        self.heap.append(value)
        while node > 0:
            child = node
            node = (node-1)//2
            if self.compare(self.heap[node], value) <= 0:
                self.heap[child] = value
                return True
            self.heap[child] = self.heap[node]
        self.heap[node] = value
        return True

    def _merge(self, node):
        count = len(self.heap)
        value = self.heap[node]
        while node*2+1 < count:
            child = node*2+1
            right = child+1
            if right < count and self.compare(self.heap[right], self.heap[child]) < 0:
                child = right
            if self.compare(value, self.heap[child]) < 0:
                break
            self.heap[node] = self.heap[child]
            node = child
        self.heap[node] = value

    def _remove_at(self, index):
        last = self.heap.pop()
        if index < len(self.heap):
            self.heap[index] = last
            self._merge(index)  # The source does not repair upward here.

    def poll(self):
        if not self.heap:
            return None
        value = self.heap[0]
        self._remove_at(0)
        return value

    def remove(self, value):
        for index, candidate in enumerate(self.heap):
            if candidate is value:
                self._remove_at(index)
                return True
        return False


def _distance(first, second):
    dx, dy = first.x-second.x, first.y-second.y
    return math.sqrt(dx*dx+dy*dy)


class StressMajorization:
    def initialize(self, graph):
        if len(graph.nodes) <= 1:
            return
        self.graph = graph
        self.dimension = graph.option('stress.dimension', 'XY')
        self.iteration_limit = graph.option('stress.iterationLimit', 2147483647)
        self.epsilon = graph.option('stress.epsilon', 0.001)
        self.desired_edge_length = graph.option('stress.desiredEdgeLength', 100)
        self.connected_edges = {node: [] for node in graph.nodes}
        for edge in graph.edges:
            self.connected_edges[edge.source].append(edge)
            self.connected_edges[edge.target].append(edge)
        count = len(graph.nodes)
        self.apsp = [[0.0 for _ in graph.nodes] for _ in graph.nodes]
        for source in graph.nodes:
            self.dijkstra(source, self.apsp[source.id])
        self.weights = [[0.0 for _ in graph.nodes] for _ in graph.nodes]
        for i in range(count):
            for j in range(count):
                distance = self.apsp[i][j]
                self.weights[i][j] = _div(1, distance*distance)

    def dijkstra(self, source, distances):
        nodes = _PriorityQueue(lambda first, second:
            _double_compare(distances[first.id], distances[second.id]))
        marked = [False for _ in self.graph.nodes]
        distances[source.id] = 0
        for node in self.graph.nodes:
            if node.id != source.id:
                distances[node.id] = 2147483647
            nodes.offer(node)
        while nodes.heap:
            first = nodes.poll()
            marked[first.id] = True
            for edge in self.connected_edges[first]:
                if edge.source is first:
                    second = edge.target
                elif edge.target is first:
                    second = edge.source
                else:
                    raise ValueError("Node 'one' must be either source or target of edge 'edge'.")
                if marked[second.id]:
                    continue
                length = (edge.option('stress.desiredEdgeLength', 100)
                          if edge.has_option('stress.desiredEdgeLength')
                          else self.desired_edge_length)
                distance = distances[first.id]+length
                if distance < distances[second.id]:
                    distances[second.id] = distance
                    nodes.remove(second)
                    nodes.offer(second)

    def compute_new_position(self, node):
        weight_sum = x_displacement = y_displacement = 0
        for other in self.graph.nodes:
            if node is other:
                continue
            weight = self.weights[node.id][other.id]
            weight_sum += weight
            distance = _distance(node.position, other.position)
            if distance > 0 and self.dimension != 'Y':
                x_displacement += weight*(other.position.x+_div(
                    self.apsp[node.id][other.id]*(node.position.x-other.position.x), distance))
            if distance > 0 and self.dimension != 'X':
                y_displacement += weight*(other.position.y+_div(
                    self.apsp[node.id][other.id]*(node.position.y-other.position.y), distance))
        if self.dimension == 'X':
            return Vec2(_div(x_displacement, weight_sum), node.position.y)
        if self.dimension == 'Y':
            return Vec2(node.position.x, _div(y_displacement, weight_sum))
        return Vec2(_div(x_displacement, weight_sum), _div(y_displacement, weight_sum))

    def compute_stress(self):
        stress = 0
        for index, first in enumerate(self.graph.nodes):
            for second in self.graph.nodes[index+1:]:
                distance = _distance(first.position, second.position)
                displacement = distance-self.apsp[first.id][second.id]
                stress += self.weights[first.id][second.id]*displacement*displacement
        return stress

    def done(self, count, previous, current):
        return (previous == 0 or _div(previous-current, previous) < self.epsilon
                or count >= self.iteration_limit)

    def execute(self):
        if len(self.graph.nodes) <= 1:
            return
        count = 0
        previous = self.compute_stress()
        current = math.inf
        while True:
            if count > 0:
                previous = current
            for node in self.graph.nodes:
                if node.option('stress.fixed', False):
                    continue
                position = self.compute_new_position(node)
                # The original reset().add() retains the same mutable object.
                node.position.x = node.position.y = 0
                node.position.x += position.x
                node.position.y += position.y
            current = self.compute_stress()
            finished = self.done(count, previous, current)
            count += 1
            if finished:
                break


def _layout(state, node, monitor=None):
    if monitor is not None:
        monitor.begin('ELK Stress', 1)
    if not state.option(node, 'interactive', False):
        from .force import _layout as force_layout
        force_layout(state, node, monitor.sub_task(1) if monitor is not None else None)
    elif not state.option(node, 'omitNodeMicroLayout', False):
        state.node_micro_layout(node)
    graph = import_graph(state, node)
    components = split_components(graph)
    majorization = StressMajorization()
    for component in components:
        if len(component.nodes) <= 1:
            continue
        majorization.initialize(component)
        majorization.execute()
        for label in component.labels:
            label.refresh_position()
    apply_layout(recombine_components(components))
    if monitor is not None:
        monitor.done()


def layout_stress(graph, options=None, *, monitor=None):
    from ..execution.json_transfer import JsonLayoutSession
    state = JsonLayoutSession(graph, options)
    _layout(state, state.graph, monitor)
    return state.export()
