# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Guava fuzzy comparison: Copyright (C) 2011 The Guava Authors, Apache-2.0.
# Fixed elkjs0.12.1 worker TD01-TD06, independently reviewed E19 source.
# SHA256 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Real Bowyer-Watson triangulation and naive spanning-tree construction.

Native scalar hashing and narrow bucket holders implement the observed value
protocol without copying GWT runtime classes. Hash collisions and original
asymmetric degenerate triangle equality remain part of that protocol.
"""
from __future__ import annotations
import math
from .layered.graph import Vec2
from .layered.ports import _source_sort
from .layered.components import _double_compare
from .fixed import _div
from .radial import _maximum


class TEdge:
    def __init__(self, first, second):
        self.u = first
        self.v = second

    def source_equals(self, other):
        return isinstance(other, TEdge) and (
            value_equals(self.u, other.u) and value_equals(self.v, other.v)
            or value_equals(self.u, other.v) and value_equals(self.v, other.u))


class TTriangle:
    def __init__(self, first, second, third):
        self.a, self.b, self.c = first, second, third
        self.t_edges = [TEdge(first, second), TEdge(second, third), TEdge(third, first)]
        self.vertices = [first, second, third]
        ab = Vec2(second.x-first.x, second.y-first.y)
        ac = Vec2(third.x-first.x, third.y-first.y)
        bc = Vec2(third.x-second.x, third.y-second.y)
        e = ab.x*(first.x+second.x)+ab.y*(first.y+second.y)
        f = ac.x*(first.x+third.x)+ac.y*(first.y+third.y)
        g = 2*(ab.x*bc.y-ab.y*bc.x)
        self.circumcenter = Vec2(_div(ac.y*e-ab.y*f, g), _div(ab.x*f-ac.x*e, g))

    def contains(self, vertex):
        return any(value_equals(vertex, stored) for stored in self.vertices)

    def source_equals(self, other):
        return isinstance(other, TTriangle) and self.contains(other.a) and self.contains(other.b) and self.contains(other.c)


class Tree:
    def __init__(self, node):
        self.node = node
        self.children = []


def value_equals(first, second):
    if first is second:
        return True
    if isinstance(first, Vec2):
        return isinstance(second, Vec2) and first.x == second.x and first.y == second.y
    if isinstance(first, (TEdge, TTriangle)):
        return first.source_equals(second)
    return False


def _fold32(value):
    value &= 0xffffffff
    return value-0x100000000 if value >= 0x80000000 else value


def _scalar_hash(value):
    """Original adapter for observed saturating signed32 truncation, not round."""
    if value != value:
        return 0
    if value >= 2147483647:
        return 2147483647
    if value <= -2147483648:
        return -2147483648
    return int(value)


def _reverse32(value):
    # Native fixed-width bit representation; no GWT nibble table is copied.
    source, result = value & 0xffffffff, 0
    for _ in range(32):
        result = (result << 1) | (source & 1)
        source >>= 1
    return _fold32(result)


def value_hash(value):
    if value is None:
        return 0
    if isinstance(value, Vec2):
        return _scalar_hash(value.x)+_reverse32(_scalar_hash(value.y))
    if isinstance(value, TEdge):
        return value_hash(value.u)+value_hash(value.v)
    if isinstance(value, TTriangle):
        return value_hash(value.a)+value_hash(value.b)+value_hash(value.c)
    raise TypeError('The native value holder supports geometric source keys only')


class ValueMap:
    """Caller-specific native value holder; bucket order is observable.

    Comparisons always call lookup/new key equality against the stored key.
    The observed triangle relation can be asymmetric for degenerate triangles.
    This is not a general-purpose GWT Map API or runtime implementation.
    """
    def __init__(self, hash_function=value_hash, equal=value_equals):
        self.buckets = {}
        self.hash_function, self.equal = hash_function, equal
        self.count = 0

    def _bucket(self, key):
        return self.buckets.get(_fold32(self.hash_function(key)), [])

    def contains(self, key):
        return any(self.equal(key, entry[0]) for entry in self._bucket(key))

    def get(self, key):
        for entry in self._bucket(key):
            if self.equal(key, entry[0]):
                return entry[1]
        return None

    def put(self, key, value):
        code = _fold32(self.hash_function(key))
        bucket = self.buckets.setdefault(code, [])
        for entry in bucket:
            if self.equal(key, entry[0]):
                previous = entry[1]
                entry[1] = value
                return previous
        bucket.append([key, value])
        self.count += 1
        return None

    def remove(self, key):
        code = _fold32(self.hash_function(key))
        bucket = self.buckets.get(code, [])
        for index, entry in enumerate(bucket):
            if self.equal(key, entry[0]):
                previous = entry[1]
                del bucket[index]
                if not bucket:
                    del self.buckets[code]
                self.count -= 1
                return previous
        return None

    def __iter__(self):
        for bucket in self.buckets.values():
            for entry in bucket:
                yield entry[0]

    def __len__(self):
        return self.count


class ValueSet:
    def __init__(self, values=()):
        self.map = ValueMap()
        self.add_all(values)

    def add(self, value):
        return self.map.put(value, self) is None

    def add_all(self, values):
        changed = False
        for value in values:
            changed = self.add(value) or changed
        return changed

    def remove(self, value):
        return self.map.remove(value) is not None

    def contains(self, value):
        return self.map.contains(value)

    def __iter__(self):
        return iter(self.map)

    def __len__(self):
        return len(self.map)


def _minimum(first, second):
    return -_maximum(-first, -second)


def _distance(first, second):
    dx, dy = first.x-second.x, first.y-second.y
    return math.sqrt(dx*dx+dy*dy)


def _fuzzy_compare(first, second):
    # Separate fixed scalar caller: common fuzzyCompare tolerance is 1e-4.
    if abs(first-second) <= 1e-4 or first == second or math.isnan(first) and math.isnan(second):
        return 0
    if first < second: return -1
    if first > second: return 1
    return int(math.isnan(first))-int(math.isnan(second))


def triangulate(vertices):
    upper, lower = Vec2(math.inf, math.inf), Vec2(-math.inf, -math.inf)
    for vertex in vertices:
        upper.x, upper.y = _minimum(upper.x, vertex.x), _minimum(upper.y, vertex.y)
        lower.x, lower.y = _maximum(lower.x, vertex.x), _maximum(lower.y, vertex.y)
    extent = Vec2(lower.x-upper.x, lower.y-upper.y)
    super_triangle = TTriangle(Vec2(upper.x-50, upper.y-extent.x-50),
        Vec2(upper.x-50, lower.y+extent.x+50),
        Vec2(lower.x+extent.y/2+50, upper.y+extent.y/2))
    triangles = ValueSet([super_triangle])
    for vertex in vertices:
        invalid = []
        for triangle in triangles:
            _distance(triangle.circumcenter, triangle.a)  # Source discarded call.
            if _fuzzy_compare(_distance(triangle.circumcenter, vertex),
                              _distance(triangle.circumcenter, triangle.a)) < 0:
                invalid.append(triangle)
        boundary = []
        for triangle in invalid:
            for edge in triangle.t_edges:
                on_boundary = True
                for other in invalid:
                    if other is not triangle and any(value_equals(edge, existing) for existing in other.t_edges):
                        on_boundary = False
                if on_boundary:
                    boundary.append(edge)
        # This actual caller's invalid list cannot outnumber the source set;
        # original removeAll therefore takes its remove-each-input branch.
        for triangle in invalid:
            triangles.remove(triangle)
        for edge in boundary:
            triangles.add(TTriangle(vertex, edge.u, edge.v))
    edges = ValueSet()
    for triangle in triangles:
        edges.add_all(triangle.t_edges)
    for edge in list(edges):
        if super_triangle.contains(edge.u) or super_triangle.contains(edge.v):
            edges.remove(edge)
    return edges


def create_spanning_tree(edges, root, cost_function):
    weights = ValueMap()
    for edge in edges:
        weights.put(edge, cost_function(edge))
    ordered = list(edges)
    _source_sort(ordered, lambda first, second: _double_compare(weights.get(first), weights.get(second)))
    # The source uses LinkedHashSet after sorting, not hash-bucket traversal.
    remaining = []
    for edge in ordered:
        if not any(value_equals(edge, stored) for stored in remaining):
            remaining.append(edge)
    result = Tree(root)
    nodes = ValueMap()
    nodes.put(root, result)
    while remaining:
        selected = None
        for index, edge in enumerate(remaining):
            if weights.get(edge) <= math.inf:
                if nodes.contains(edge.u) and not nodes.contains(edge.v):
                    selected = index, edge.v, edge.u
                    break
                if nodes.contains(edge.v) and not nodes.contains(edge.u):
                    selected = index, edge.u, edge.v
                    break
        if selected is None:
            break
        index, next_node, in_tree = selected
        child = Tree(next_node)
        nodes.get(in_tree).children.append(child)
        nodes.put(next_node, child)
        remaining.pop(index)
    return result


def delaunay_phase(graph, monitor=None):
    if monitor is not None: monitor.begin('Delaunay triangulation', 1)
    edges = triangulate([node.original_vertex for node in graph.vertices])
    if graph.t_edges is None:
        graph.t_edges = edges
    else:
        graph.t_edges.add_all(edges)
    if monitor is not None: monitor.done()


def spanning_tree_phase(graph, monitor=None, *, maximum=False):
    if monitor is not None:
        monitor.begin('Maximum spanning tree construction' if maximum else 'Minimum spanning tree construction', 1)
    source = graph.preferred_root if graph.preferred_root is not None else graph.vertices[0]
    root = source.vertex if maximum else source.original_vertex
    cost = (lambda edge: -graph.cost_function(edge)) if maximum else graph.cost_function
    tree = create_spanning_tree(graph.t_edges, root, cost)
    mapping = ValueMap()
    for node in graph.vertices:
        mapping.put(node.original_vertex, node)
    converted = Tree(mapping.get(tree.node))
    work = [(converted, iter(tree.children))]
    while work:
        parent, children = work[-1]
        try:
            child = next(children)
        except StopIteration:
            work.pop()
            continue
        native_child = Tree(mapping.get(child.node))
        parent.children.append(native_child)
        work.append((native_child, iter(child.children)))
    graph.tree = converted
    if monitor is not None: monitor.done()
