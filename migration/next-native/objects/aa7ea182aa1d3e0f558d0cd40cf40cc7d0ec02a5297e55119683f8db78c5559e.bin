# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs0.12.1 worker275e6caf, lines46931–47587.
"""Multi-edge wrapping with linked breaking-point chains."""
from dataclasses import dataclass
import math

from ...execution.diagnostics import BasicProgressMonitor
from ...execution.node_micro import VectorChain
from .graph import Layer, set_layer, set_source, set_target
from .wrapping import (GraphStats, read, incoming, outgoing, new_node, new_port,
                       new_edge, cut_indexes, validify_cuts, insert_dummies)
from .orthogonal_general import get_junction_points
from .long_edges_general import join_at
from ..radial import IdentitySet


@dataclass(eq=False)
class BPInfo:
    start: object
    end: object
    node_start_edge: object
    start_end_edge: object
    original_edge: object
    prev: object = None
    next: object = None
    start_in_layer_dummy: object = None
    start_in_layer_edge: object = None
    end_in_layer_dummy: object = None
    end_in_layer_edge: object = None


@dataclass(eq=False)
class Cut:
    index: int
    assigned: bool = False
    new_index: int = 0
    prev: object = None
    next: object = None

    def available(self):
        current = self
        while current is not None and current.assigned:
            current = current.next
        return current

    def offset(self):
        delta = self.new_index - self.index
        self.index += delta
        current = self.prev
        while current is not None and not current.assigned:
            current.index += delta
            current = current.prev
        current = self.next
        while current is not None and not current.assigned:
            current.index += delta
            current = current.next


def _is_start(node):
    info = node.properties.get('BREAKING_POINT_INFO')
    return info is not None and info.start is node


def _is_end(node):
    info = node.properties.get('BREAKING_POINT_INFO')
    return info is not None and info.end is node


def _spans(graph):
    opened = IdentitySet(graph)
    # Source HashSet is queried only for membership/size on this path.
    active = set()
    result = [0] * (len(graph.layers) + 1)
    for i, layer in enumerate(graph.layers):
        result[i] = len(active)
        for node in layer.nodes:
            for edge in outgoing(node):
                opened.add(edge)
                active.add(edge)
        for node in layer.nodes:
            for edge in incoming(node):
                graph.identity_hash(edge) if hasattr(graph, 'identity_hash') else opened.contains(edge)
                active.discard(edge)
    return result


def _improve_cuts(graph, indexes):
    cuts = [Cut(index) for index in indexes]
    for before, after in zip(cuts, cuts[1:]):
        before.next, after.prev = after, before
    spans = _spans(graph)
    result = []
    for _ in cuts:
        left = None
        right = cuts[0].available()
        best = None
        best_score = math.inf
        for index in range(1, len(graph.layers)):
            rd = abs(right.index - index) if right is not None else abs(index - left.index) + 1
            ld = abs(index - left.index) if left is not None else rd + 1
            hit, distance = (left, ld) if ld < rd else (right, rd)
            try:
                score = spans[index] + math.pow(distance, read(graph, 'WRAPPING_MULTI_EDGE_DISTANCE_PENALTY'))
            except OverflowError:
                score = math.inf
            except ValueError:
                score = math.inf if distance == 0 and read(graph, 'WRAPPING_MULTI_EDGE_DISTANCE_PENALTY') < 0 else math.nan
            if score < best_score:
                best_score, best = score, hit
                best.new_index = index
            if right is not None and index == right.index:
                left = right
                right = right.next.available() if right.next is not None else None
        if best is not None:
            result.append(best.new_index)
            best.assigned = True
            best.offset()
    result.sort()
    return result


def _copy_model_order(target, source):
    value = source.properties.get('MODEL_ORDER')
    tokens = getattr(source, 'integer_box_identities', {})
    target.properties.set_property('MODEL_ORDER', value, integer_box=tokens.get('MODEL_ORDER'))


def _apply_cuts(graph, cuts):
    iterator = iter(cuts)
    cut = next(iterator)
    already = IdentitySet(graph)
    opened = []
    opened_set = set()
    cursor = index = 0
    count = 0
    while cursor < len(graph.layers):
        layer = graph.layers[cursor]
        cursor += 1
        for node in layer.nodes:
            for edge in outgoing(node):
                if hasattr(graph, 'identity_hash'):
                    graph.identity_hash(edge)
                if edge not in opened_set:
                    opened.append(edge)
                    opened_set.add(edge)
            for edge in incoming(node):
                if hasattr(graph, 'identity_hash'):
                    graph.identity_hash(edge)
                if edge in opened_set:
                    opened_set.remove(edge)
                    opened.remove(edge)
        if index + 1 == cut:
            first, second = Layer(graph), Layer(graph)
            graph.layers[cursor:cursor] = [first, second]
            cursor += 2
            for original in opened:
                if not already.contains(original):
                    count += 1
                    already.add(original)
                start, end = new_node(graph, 'BREAKING_POINT'), new_node(graph, 'BREAKING_POINT')
                start.properties['PORT_CONSTRAINTS'] = end.properties['PORT_CONSTRAINTS'] = 'FIXED_SIDE'
                set_layer(start, first)
                p1i, p1o = new_port(start, 'WEST'), new_port(start, 'EAST')
                set_layer(end, second)
                p2i, p2o = new_port(end, 'WEST'), new_port(end, 'EAST')
                beginning = new_edge(original.source, p1i)
                _copy_model_order(beginning, original)
                middle = new_edge(p1o, p2i)
                _copy_model_order(middle, original)
                set_source(original, p2o)
                info = BPInfo(start, end, beginning, middle, original)
                start.properties['BREAKING_POINT_INFO'] = end.properties['BREAKING_POINT_INFO'] = info
                previous = beginning.source.owner
                if previous.type == 'BREAKING_POINT':
                    previous_info = previous.properties.get('BREAKING_POINT_INFO')
                    previous_info.next = info
                    info.prev = previous_info
            cut = next(iterator, None)
            if cut is None:
                break
        index += 1
    return count


def breaking_point_inserter(graph, *, monitor=None):
    monitor = monitor if monitor is not None else BasicProgressMonitor()
    monitor.begin('Breaking Point Insertion', 1)
    stats = GraphStats(graph)
    cuts = cut_indexes(graph, stats)
    if read(graph, 'WRAPPING_MULTI_EDGE_IMPROVE_CUTS'):
        cuts = _improve_cuts(graph, cuts)
    if 'WRAPPING_VALIDIFY_STRATEGY' in graph.properties:
        cuts = validify_cuts(graph, stats, cuts)
    if cuts:
        _apply_cuts(graph, cuts)
    monitor.done()


def _update_indexes_after(node):
    for following in node.layer.nodes[node.id + 1:]:
        following.id -= 1


def _next_long(node, forwards):
    for edge in outgoing(node) if forwards else incoming(node):
        other = edge.target.owner if edge.source.owner is node else edge.source.owner
        if other.type == 'LONG_EDGE' and other.layer is not node.layer:
            return other
    return None


def _in_layer_dummy(node):
    if node.type == 'LONG_EDGE':
        for port in node.ports:
            for edge in list(port.incoming_edges) + list(port.outgoing_edges):
                if edge.source.owner is not edge.target.owner:
                    other = edge.target.owner if edge.source.owner is node else edge.source.owner
                    if other.layer is node.layer:
                        return True
    return False


def _adjacent(first, second, forwards):
    start, end = (second, first) if forwards else (first, second)
    for node in first.layer.nodes[start.id + 1:end.id]:
        if node.type != 'BREAKING_POINT' and not _in_layer_dummy(node):
            return False
    return True


def _drop_dummies(node, dummy, forwards, force):
    first, second = _next_long(node, forwards), _next_long(dummy, forwards)
    changed = False
    while first is not None and second is not None:
        if not force and not _adjacent(first, second, forwards):
            break
        following1, following2 = _next_long(first, forwards), _next_long(second, forwards)
        _update_indexes_after(dummy)
        _update_indexes_after(node)
        layer = first.layer
        join_at(first)
        join_at(second)
        if forwards:
            set_layer(dummy, layer, second.id)
            dummy.id = second.id
            set_layer(node, layer, first.id + 1)
            node.id = first.id
        else:
            set_layer(node, layer, first.id)
            node.id = first.id
            set_layer(dummy, layer, second.id + 1)
            dummy.id = second.id
        set_layer(first, None)
        set_layer(second, None)
        first, second = following1, following2
        changed = True
    return changed


def _improve_multi_cut(graph):
    for layer in graph.layers:
        for node in list(layer.nodes):
            if not _is_start(node):
                continue
            info = node.properties.get('BREAKING_POINT_INFO')
            if info.prev is not None or info.next is None:
                continue
            current, following = info, info.next
            while following is not None:
                _drop_dummies(following.start, following.start_in_layer_dummy, False, True)
                for item in (current.end, following.start, following.start_in_layer_dummy, following.end_in_layer_dummy):
                    _update_indexes_after(item)
                set_target(following.end_in_layer_edge, current.end_in_layer_edge.target)
                set_target(current.end_in_layer_edge, None)
                for item in (current.end, following.start, following.start_in_layer_dummy, following.end_in_layer_dummy):
                    set_layer(item, None)
                new = BPInfo(current.start, following.end, current.node_start_edge,
                             following.start_end_edge, following.original_edge)
                new.start_in_layer_dummy = current.start_in_layer_dummy
                new.start_in_layer_edge = current.start_in_layer_edge
                new.end_in_layer_dummy = current.end_in_layer_dummy
                new.end_in_layer_edge = following.end_in_layer_edge
                new.prev, new.next = current.prev, following.next
                current.start.properties['BREAKING_POINT_INFO'] = following.end.properties['BREAKING_POINT_INFO'] = new
                following, current = following.next, new


def _improve_long(graph, forwards):
    while True:
        changed = False
        layers = reversed(graph.layers) if forwards else iter(graph.layers)
        for layer in layers:
            nodes = list(layer.nodes)
            # Source reverse_0(nodes) returns a view whose unused return has no effect.
            for node in nodes:
                if (_is_end(node) if forwards else _is_start(node)):
                    info = node.properties.get('BREAKING_POINT_INFO')
                    dummy = info.end_in_layer_dummy if forwards else info.start_in_layer_dummy
                    changed = _drop_dummies(node, dummy, forwards, False)
        if not changed:
            break


def breaking_point_processor(graph, *, monitor=None):
    from .cycles_general import reverse_edge
    monitor = monitor if monitor is not None else BasicProgressMonitor()
    monitor.begin('Breaking Point Processor', 1)
    graph.layers.insert(0, Layer(graph))
    cursor, index, reverse = 1, 1, False
    while cursor < len(graph.layers):
        layer = graph.layers[cursor]
        cursor += 1
        target = graph.layers[index]
        nodes = list(layer.nodes)
        offset = len(nodes)
        for node in nodes:
            set_layer(node, target)
        if reverse:
            for node in reversed(nodes):
                for edge in list(incoming(node)):
                    reverse_edge(edge, True)
                    graph.properties['CYCLIC'] = True
                    generated = insert_dummies(graph, edge, offset)
                    info = node.properties.get('BREAKING_POINT_INFO')
                    start_edge = generated[-1]
                    info.start_in_layer_dummy = start_edge.source.owner
                    info.start_in_layer_edge = start_edge
                    info.end_in_layer_dummy = edge.target.owner
                    info.end_in_layer_edge = edge
            reverse = False
        elif nodes and nodes[0].type == 'BREAKING_POINT':
            reverse, index = True, -1
        index += 1
    graph.layers[:] = [layer for layer in graph.layers if layer.nodes]
    if read(graph, 'WRAPPING_MULTI_EDGE_IMPROVE_WRAPPED_EDGES'):
        for layer in graph.layers:
            for i, node in enumerate(layer.nodes):
                node.id = i
        _improve_multi_cut(graph)
        _improve_long(graph, True)
        _improve_long(graph, False)
    monitor.done()


def breaking_point_remover(graph, *, monitor=None):
    from .property_access import read_layered_scalar
    monitor = monitor if monitor is not None else BasicProgressMonitor()
    monitor.begin('Breaking Point Removing', 1)
    routing = read_layered_scalar(graph, 'EDGE_ROUTING', 'EDGE_ROUTING')
    for layer in graph.layers:
        for node in list(layer.nodes):
            if not _is_end(node):
                continue
            info = node.properties.get('BREAKING_POINT_INFO')
            if info.next is not None:
                continue
            while info is not None:
                beginning, middle, original = info.node_start_edge, info.start_end_edge, info.original_edge
                bends = []
                if routing == 'SPLINES':
                    first = beginning.properties.get('SPLINE_ROUTE_START')
                    second = middle.properties.get('SPLINE_ROUTE_START')
                    third = original.properties.get('SPLINE_ROUTE_START')
                    for segment in second:
                        segment.inverse_order = True
                    original.properties['SPLINE_ROUTE_START'] = list(first) + list(reversed(second)) + list(third)
                    original.properties['SPLINE_EDGE_CHAIN'] = (list(beginning.properties.get('SPLINE_EDGE_CHAIN'))
                        + list(reversed(middle.properties.get('SPLINE_EDGE_CHAIN')))
                        + list(original.properties.get('SPLINE_EDGE_CHAIN')))
                    original.properties['SPLINE_SURVIVING_EDGE'] = original
                    for edge in (beginning, middle):
                        edge.properties['SPLINE_ROUTE_START'] = edge.properties['SPLINE_EDGE_CHAIN'] = None
                else:
                    bends.extend(beginning.bend_points)
                    if routing == 'POLYLINE':
                        bends.append(info.start.pos)
                    bends.extend(reversed(middle.bend_points))
                    if routing == 'POLYLINE':
                        bends.append(info.end.pos)
                    bends.extend(original.bend_points)
                original.bend_points[:] = bends
                set_source(original, beginning.source)
                chains = [get_junction_points(edge) for edge in (beginning, middle, original)]
                if any(chain is not None for chain in chains):
                    joined = VectorChain()
                    for chain in reversed(chains):
                        if chain is not None:
                            joined.extend(chain)
                    original.properties['JUNCTION_POINTS'] = joined
                for edge in (middle, beginning):
                    set_source(edge, None)
                    set_target(edge, None)
                set_layer(info.end, None)
                set_layer(info.start, None)
                info = info.prev
    monitor.done()
