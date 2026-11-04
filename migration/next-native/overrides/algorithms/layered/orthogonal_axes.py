# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# P22E / HOST16/root/orthogonal-axes-source-review-01, source proposed by A.
"""North/south strategies over the shared full orthogonal scalar engine."""
from . import orthogonal_general as scalar
from .graph import Vec2
from ..disco import _IdentityMap


def _port_x(port):
    return port.owner.pos.x + port.pos.x + port.anchor.x


def _vector_sum_x(port):
    result = 0.0
    result += port.owner.pos.x
    result += port.pos.x
    result += port.anchor.x
    return result


class _AxesGenerator(scalar._Generator):
    def __init__(self, direction, edge_spacing):
        self.direction = direction
        self.source_side = 'SOUTH' if direction == 1 else 'NORTH'
        self.target_side = 'NORTH' if direction == 1 else 'SOUTH'
        super().__init__(edge_spacing)

    def _add_ports(self, segment, port, mapping):
        def enter(current):
            mapping.put(current, segment)
            segment.ports.append(current)
            values = segment.incoming if current.side == self.source_side else segment.outgoing
            scalar._insert_sorted(values, _port_x(current))
            scalar._extent(segment)
            return iter([edge.source for edge in current.incoming_edges]
                        + [edge.target for edge in current.outgoing_edges])
        frames = [enter(port)]
        while frames:
            try:
                following = next(frames[-1])
            except StopIteration:
                frames.pop()
                continue
            if mapping.get(following) is None:
                frames.append(enter(following))

    def _create_segments(self, nodes, side, segments, mapping):
        if nodes is None:
            return
        for node in nodes:
            for port in node.ports:
                if port.side == side and port.outgoing_edges and mapping.get(port) is None:
                    segment = scalar._Segment()
                    segments.append(segment)
                    self._add_ports(segment, port, mapping)

    def _junction(self, edge, segment, position):
        key = position.x, position.y
        if key in self.created_junctions:
            return
        p = position.x
        inside = p > segment.start and p < segment.end
        boundary = False
        if segment.incoming and segment.outgoing:
            boundary = boundary | (abs(p - segment.incoming[0]) < scalar.EPSILON
                                   and abs(p - segment.outgoing[0]) < scalar.EPSILON)
            boundary = boundary | (abs(p - segment.incoming[-1]) < scalar.EPSILON
                                   and abs(p - segment.outgoing[-1]) < scalar.EPSILON)
        if inside or boundary:
            point = Vec2(position.x, position.y)
            scalar.get_junction_points(edge).append(point)
            self.created_junctions.add(key)

    def _slot_position(self, start, slot):
        if self.direction == 1:
            return start + slot * self.edge_spacing
        return start - slot * self.edge_spacing

    def _bends(self, segment, start_position):
        if segment.split_partner is not None and segment.split_by is None:
            return
        segment_y = self._slot_position(start_position, segment.slot)
        for port in segment.ports:
            source_x = _vector_sum_x(port)
            for edge in port.outgoing_edges:
                if edge.source.owner is edge.target.owner:
                    continue
                target_x = _vector_sum_x(edge.target)
                if abs(source_x - target_x) > scalar.EPSILON:
                    current_y, current = segment_y, segment
                    point = Vec2(source_x, current_y)
                    edge.bend_points.append(point)
                    self._junction(edge, current, point)
                    partner = segment.split_partner
                    if partner is not None:
                        split_x = partner.incoming[0]
                        point = Vec2(split_x, current_y)
                        edge.bend_points.append(point)
                        self._junction(edge, current, point)
                        current_y = self._slot_position(start_position, partner.slot)
                        current = partner
                        point = Vec2(split_x, current_y)
                        edge.bend_points.append(point)
                        self._junction(edge, current, point)
                    point = Vec2(target_x, current_y)
                    edge.bend_points.append(point)
                    self._junction(edge, current, point)

    def route(self, graph, source_nodes, target_nodes, start_position):
        segments, mapping = [], _IdentityMap(graph)
        self._create_segments(source_nodes, self.source_side, segments, mapping)
        self._create_segments(target_nodes, self.target_side, segments, mapping)
        incoming = scalar._minimum_difference(value for segment in segments for value in segment.incoming)
        outgoing = scalar._minimum_difference(value for segment in segments for value in segment.outgoing)
        self.critical_threshold = 0.2 * scalar._minimum(incoming, outgoing)
        critical = 0
        for first in range(len(segments) - 1):
            for second in range(first + 1, len(segments)):
                critical += self._create_dependency(segments[first], segments[second])
        random = graph.properties.get('RANDOM')
        if critical >= 2:
            self._split_segments(scalar._detect_cycles(segments, True, random), segments)
        scalar._break_cycles(segments, random)
        scalar._number_slots(segments)
        rank = -1
        for segment in segments:
            if abs(segment.start - segment.end) < scalar.EPSILON:
                continue
            rank = max(rank, segment.slot)
            self._bends(segment, start_position)
        self.created_junctions.clear()
        return rank + 1


def routing_generator(direction, edge_spacing):
    if type(direction) is int:
        if direction == 0:
            return scalar._Generator(edge_spacing)
        if direction in (1, 2):
            return _AxesGenerator(direction, edge_spacing)
    raise ValueError('Invalid orthogonal routing direction')
