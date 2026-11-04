# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs0.12.1 worker275e6caf, HighDegreeNodeLayeringProcessor37620–37823.
"""Separate bounded-height trees around actual high-degree nodes."""
from .graph import Layer, set_layer
from .wrapping import incoming, outgoing, read


def _connected(node):
    for port in node.ports:
        yield from port.incoming_edges
        yield from port.outgoing_edges


def _other(edge, node):
    return edge.target.owner if edge.source.owner is node else edge.source.owner


def _single(node, selector):
    connection = None
    for edge in selector(node):
        other = _other(edge, node)
        if connection is None:
            connection = other
        elif connection is not other:
            return False
    return True


class HighDegreeNodeLayeringProcessor:
    source_name = 'HighDegreeNodeLayeringProcessor'

    def get_layout_processor_configuration(self, graph):
        return None

    def _tree_height(self, root, ancestors, descendants):
        # Iterator frames preserve the source recursive return points without a
        # host recursion-depth restriction or an extra cycle/size admission cap.
        stack = []
        node = root
        while True:
            if sum(1 for _ in _connected(node)) >= self.degree_threshold or not _single(node, ancestors):
                result = -1
            else:
                edges = iter(descendants(node))
                first = next(edges, None)
                if first is None:
                    result = 1
                else:
                    stack.append([edges, 0, node])
                    node = _other(first, node)
                    continue
            while stack:
                frame = stack[-1]
                if result == -1:
                    stack.pop()
                    continue
                frame[1] = max(frame[1], result)
                if frame[1] > self.tree_height_threshold - 1:
                    stack.pop()
                    result = -1
                    continue
                edge = next(frame[0], None)
                if edge is not None:
                    node = _other(edge, frame[2])
                    break
                result = frame[1] + 1
                stack.pop()
            else:
                return result

    def _information(self, node):
        roots = [None, None]
        maxima = [-1, -1]
        for i, (edges, ancestors, descendants) in enumerate(((incoming(node), outgoing, incoming),
                                                          (outgoing(node), incoming, outgoing))):
            for edge in edges:
                if edge.source.owner is edge.target.owner:
                    continue
                other = edge.source.owner if i == 0 else edge.target.owner
                if _single(other, ancestors):
                    height = self._tree_height(other, ancestors, descendants)
                    if height == -1:
                        continue
                    maxima[i] = max(maxima[i], height)
                    if roots[i] is None:
                        roots[i] = []
                    roots[i].append(other)
        return roots, maxima

    def _move_tree(self, root, selector, layers):
        set_layer(root, layers[0])
        stack = [(root, iter(selector(root)), 1)]
        while stack:
            node, edges, depth = stack[-1]
            edge = next(edges, None)
            if edge is None:
                stack.pop()
            else:
                other = _other(edge, node)
                set_layer(other, layers[depth])
                stack.append((other, iter(selector(other)), depth + 1))

    def process(self, graph, monitor=None):
        # The actual processor does not touch the passed monitor.
        self.graph = graph
        self.degree_threshold = read(graph, 'HIGH_DEGREE_NODES_THRESHOLD')
        self.tree_height_threshold = read(graph, 'HIGH_DEGREE_NODES_TREE_HEIGHT')
        if self.tree_height_threshold == 0:
            self.tree_height_threshold = 2147483647
        cursor = 0
        while cursor < len(graph.layers):
            layer = graph.layers[cursor]
            cursor += 1
            selected = []
            inc_max = out_max = -1
            for node in layer.nodes:
                if sum(1 for _ in _connected(node)) >= self.degree_threshold:
                    roots, maxima = self._information(node)
                    inc_max = max(inc_max, maxima[0])
                    out_max = max(out_max, maxima[1])
                    selected.append(roots)
            before = []
            for _ in range(inc_max):
                new = Layer(graph)
                graph.layers.insert(cursor - 1, new)
                cursor += 1
                before.insert(0, new)
            for roots in selected:
                if roots[0] is not None:
                    for node in roots[0]:
                        self._move_tree(node, incoming, before)
            after = []
            for _ in range(out_max):
                new = Layer(graph)
                graph.layers.insert(cursor, new)
                cursor += 1
                after.append(new)
            for roots in selected:
                if roots[1] is not None:
                    for node in roots[1]:
                        self._move_tree(node, outgoing, after)
        graph.layers[:] = [layer for layer in graph.layers if layer.nodes]
