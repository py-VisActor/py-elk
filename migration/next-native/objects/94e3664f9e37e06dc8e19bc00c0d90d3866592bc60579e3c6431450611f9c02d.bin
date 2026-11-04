# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# General mechanical port of fixed elkjs0.12.1 direction0 orthogonal routing.
# Commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source closure: HOST-12/V/orthogonal-{entry,general-math}-source-review-01.
# Historical routing.py remains frozen; general IEEE/cast/typed-chain adapters separate.
# Exact external Java build unresolved. See pyelk/_licenses/NOTICE-E05.md.
"""General direction0 orthogonal routing over the actual preprocessed LGraph.

Port traversal, slot/cycle/splitting arithmetic and caller order follow the
fixed source. No old admission function or bounded driver is invoked. Required
intermediate transformations remain the actual pipeline caller's work.
"""
from collections import deque
from dataclasses import dataclass, field
from functools import cmp_to_key
import math

from .graph import LEdge, Vec2
from ..disco import _IdentityMap
from ...execution.node_micro import VectorChain
from ...execution.diagnostics import BasicProgressMonitor
from .placement import _min as _minimum, _max as _maximum
from .property_access import read_layered_scalar

EPSILON = 0.001
DOUBLE_MAX = 1.7976931348623157e308
_P = "org.eclipse.elk."


def _sum_i32(values):
    # Actual IntSummaryStatistics long sum -> toInt_0 low signed32 bits.
    total = sum(values)
    return (int(total) + (1 << 31)) % (1 << 32) - (1 << 31)


class _CoordinateSet:
    """Membership only: KVector primitive coordinate equality, not tuple ids."""
    def __init__(self):
        self.values = set()
        self.nan_count = 0

    def __contains__(self, value):
        x, y = value
        return x == x and y == y and value in self.values

    def add(self, value):
        x, y = value
        if x != x or y != y:
            self.nan_count += 1
        else:
            self.values.add(value)

    def clear(self):
        self.values.clear()
        self.nan_count = 0

    def __len__(self):
        return len(self.values) + self.nan_count


def get_junction_points(edge):
    """Keep an actual typed chain, including an existing empty chain, by ref."""
    if not isinstance(edge, LEdge):
        raise TypeError('Expected an actual LEdge')
    value = edge.properties.get('JUNCTION_POINTS')
    if value is None:
        value = VectorChain()
        edge.properties['JUNCTION_POINTS'] = value
    if not isinstance(value, list) or any(not isinstance(point, Vec2)for point in value):
        raise TypeError('Actual ordered native vector chain required')
    return value


def _remove_identity(items, item):
    for index, candidate in enumerate(items):
        if candidate is item:
            del items[index]
            return


@dataclass(eq=False)
class _Segment:
    ports: list = field(default_factory=list)
    incoming: list = field(default_factory=list)
    outgoing: list = field(default_factory=list)
    incoming_dependencies: list = field(default_factory=list)
    outgoing_dependencies: list = field(default_factory=list)
    start: float = math.nan
    end: float = math.nan
    mark: int = 0
    in_weight: int = 0
    out_weight: int = 0
    critical_in_weight: int = 0
    critical_out_weight: int = 0
    slot: int = 0
    split_by: object = None
    split_partner: object = None


@dataclass(eq=False)
class _Dependency:
    kind: str
    weight: int
    source: object = None
    target: object = None


def _set_source(dependency, source):
    if dependency.source is not None:
        _remove_identity(dependency.source.outgoing_dependencies, dependency)
    dependency.source = source
    if source is not None:
        source.outgoing_dependencies.append(dependency)


def _set_target(dependency, target):
    if dependency.target is not None:
        _remove_identity(dependency.target.incoming_dependencies, dependency)
    dependency.target = target
    if target is not None:
        target.incoming_dependencies.append(dependency)


def _dependency(kind, source, target, weight):
    result = _Dependency(kind, weight)
    _set_source(result, source)
    _set_target(result, target)
    return result


def _remove_dependency(dependency):
    _set_source(dependency, None)
    _set_target(dependency, None)


def _compare_double(left, right):
    if left < right:
        return -1
    if left > right:
        return 1
    if left == right:
        if left == 0:
            a, b = math.copysign(1, left), math.copysign(1, right)
            return (a > b) - (a < b)
        return 0
    return 0 if math.isnan(left) and math.isnan(right) else 1 if math.isnan(left) else -1


def _sorted_distinct(values):
    result = []
    for value in sorted(values, key=cmp_to_key(_compare_double)):
        # Generated Double distinct is primitive ===: both signed zeros merge,
        # retaining the preceding natural-sort representative (negative zero).
        if not result or value != result[-1]:
            result.append(value)
    return result


def _minimum_difference(values):
    numbers = _sorted_distinct(values)
    difference = DOUBLE_MAX
    for index in range(1, len(numbers)):
        difference = _minimum(difference, numbers[index] - numbers[index - 1])
    return difference


def _insert_sorted(values, value):
    for index, current in enumerate(values):
        if current == value:
            return
        if current > value:
            values.insert(index, value)
            return
    values.append(value)


def _extent(segment):
    segment.start, segment.end = math.nan, math.nan
    for values in (segment.incoming, segment.outgoing):
        if values:
            segment.start = values[0] if math.isnan(segment.start) else _minimum(segment.start, values[0])
            segment.end = values[-1] if math.isnan(segment.end) else _maximum(segment.end, values[-1])


def _port_y(port):
    return port.owner.pos.y + port.pos.y + port.anchor.y


def _vector_sum_y(port):
    # KVector.sum starts with a zero vector and adds the three arguments.
    result = 0.0
    result += port.owner.pos.y
    result += port.pos.y
    result += port.anchor.y
    return result


def _add_port_positions(segment, port, mapping):
    def enter(current):
        mapping.put(current, segment)
        segment.ports.append(current)
        values = segment.incoming if current.side == "EAST" else segment.outgoing
        _insert_sorted(values, _port_y(current))
        _extent(segment)
        return iter([edge.source for edge in current.incoming_edges]
                    + [edge.target for edge in current.outgoing_edges])
    frames = [enter(port)]
    while frames:
        try:
            other = next(frames[-1])
        except StopIteration:
            frames.pop()
            continue
        # Source containsKey and put both request the actual shared LPort hash.
        if mapping.get(other) is None:
            frames.append(enter(other))


def _create_segments(nodes, side, segments, mapping):
    if nodes is None:
        return
    for node in nodes:
        # Source getPorts_0 uses ordered side/type predicates, not side caches.
        for port in node.ports:
            if port.side == side and port.outgoing_edges and mapping.get(port) is None:
                segment = _Segment()
                segments.append(segment)
                _add_port_positions(segment, port, mapping)


def _count_crossings(positions, start, end):
    count = 0
    for position in positions:
        if position > end:
            break
        if position >= start:
            count += 1
    return count


def _initialize(segments, critical_only):
    sources, sinks = deque(), deque()
    for index, segment in enumerate(segments):
        segment.mark = -1 - index
        segment.critical_in_weight = _sum_i32(d.weight for d in segment.incoming_dependencies if d.kind == "CRITICAL")
        segment.critical_out_weight = _sum_i32(d.weight for d in segment.outgoing_dependencies if d.kind == "CRITICAL")
        segment.in_weight = (segment.critical_in_weight if critical_only
                             else _sum_i32(d.weight for d in segment.incoming_dependencies))
        segment.out_weight = (segment.critical_out_weight if critical_only
                              else _sum_i32(d.weight for d in segment.outgoing_dependencies))
        if segment.out_weight == 0:
            sinks.append(segment)
        elif segment.in_weight == 0:
            sources.append(segment)
    return sources, sinks


def _update_neighbors(node, sources, sinks, critical_only):
    for dependency in node.outgoing_dependencies:
        if not critical_only or dependency.kind == "CRITICAL":
            target = dependency.target
            if target.mark < 0 and dependency.weight > 0:
                target.in_weight -= dependency.weight
                if dependency.kind == "CRITICAL":
                    target.critical_in_weight -= dependency.weight
                if target.in_weight <= 0 and target.out_weight > 0:
                    sources.append(target)
    for dependency in node.incoming_dependencies:
        if not critical_only or dependency.kind == "CRITICAL":
            source = dependency.source
            if source.mark < 0 and dependency.weight > 0:
                source.out_weight -= dependency.weight
                if dependency.kind == "CRITICAL":
                    source.critical_out_weight -= dependency.weight
                if source.out_weight <= 0 and source.in_weight > 0:
                    sinks.append(source)


def _linear_marks(segments, sources, sinks, critical_only, random):
    # Source TreeSet compares unique negative marks. Keys are removed before
    # mutation; the remaining order therefore stays equal to this sorted list.
    remaining = sorted(segments, key=lambda segment: segment.mark)
    base = len(segments)
    next_sink, next_source = base - 1, base + 1
    while remaining:
        while sinks:
            sink = sinks.popleft()
            _remove_identity(remaining, sink)
            sink.mark = next_sink
            next_sink -= 1
            _update_neighbors(sink, sources, sinks, critical_only)
        while sources:
            source = sources.popleft()
            _remove_identity(remaining, source)
            source.mark = next_source
            next_source += 1
            _update_neighbors(source, sources, sinks, critical_only)
        maximum, choices = -(1 << 31), []
        for segment in remaining:
            if not critical_only and segment.critical_out_weight > 0 and segment.critical_in_weight <= 0:
                choices.clear()
                choices.append(segment)
                break
            outflow = segment.out_weight - segment.in_weight
            if outflow >= maximum:
                if outflow > maximum:
                    choices.clear()
                    maximum = outflow
                choices.append(segment)
        if choices:
            chosen = choices[random.next_int(len(choices))]
            _remove_identity(remaining, chosen)
            chosen.mark = next_source
            next_source += 1
            _update_neighbors(chosen, sources, sinks, critical_only)
    shift = len(segments) + 1
    for segment in segments:
        if segment.mark < base:
            segment.mark += shift


def _detect_cycles(segments, critical_only, random):
    sources, sinks = _initialize(segments, critical_only)
    _linear_marks(segments, sources, sinks, critical_only, random)
    return [dependency for source in segments for dependency in source.outgoing_dependencies
            if (not critical_only or dependency.kind == "CRITICAL") and source.mark > dependency.target.mark]


def _break_cycles(segments, random):
    for dependency in _detect_cycles(segments, False, random):
        if dependency.weight == 0:
            _remove_dependency(dependency)
        else:
            old_source, old_target = dependency.source, dependency.target
            _set_source(dependency, old_target)
            _set_target(dependency, old_source)


def _number_slots(segments):
    sources, rightward = deque(), deque()
    for node in segments:
        node.in_weight = len(node.incoming_dependencies)
        node.out_weight = len(node.outgoing_dependencies)
        if node.in_weight == 0:
            sources.append(node)
        if node.out_weight == 0 and not node.incoming:
            rightward.append(node)
    maximum = -1
    while sources:
        node = sources.popleft()
        for dependency in node.outgoing_dependencies:
            target = dependency.target
            target.slot = max(target.slot, node.slot + 1)
            maximum = max(maximum, target.slot)
            target.in_weight -= 1
            if target.in_weight == 0:
                sources.append(target)
    if maximum > -1:
        for node in rightward:
            node.slot = maximum
        while rightward:
            node = rightward.popleft()
            for dependency in node.incoming_dependencies:
                source = dependency.source
                if source.incoming:
                    continue
                source.slot = min(source.slot, node.slot - 1)
                source.out_weight -= 1
                if source.out_weight == 0:
                    rightward.append(source)


@dataclass(eq=False)
class _Area:
    start: float
    end: float

    @property
    def size(self):
        return self.end - self.start

    @property
    def center(self):
        return (self.start + self.end) / 2


def _crossings_for_ordering(left, right):
    return (_count_crossings(left.outgoing, right.start, right.end)
            + _count_crossings(right.incoming, left.start, left.end))


def _update_rating(rating, first, second):
    left = _crossings_for_ordering(first, second)
    right = _crossings_for_ordering(second, first)
    if left == right:
        if left > 0:
            rating[0] += 2
            rating[1] += left
    else:
        rating[0] += 1
        rating[1] += min(left, right)


def _rate_area(segment, split, partner, area):
    center = area.center
    split.outgoing.clear()
    split.outgoing.append(center)
    partner.incoming.clear()
    partner.incoming.append(center)
    # Source intentionally does not recompute these temporary extents here.
    rating = [0, 0]  # dependency count, crossing count
    for dependency in segment.incoming_dependencies:
        other = dependency.source
        _update_rating(rating, split, other)
        _update_rating(rating, partner, other)
    for dependency in segment.outgoing_dependencies:
        other = dependency.target
        _update_rating(rating, split, other)
        _update_rating(rating, partner, other)
    rating[0] += 2
    rating[1] += _crossings_for_ordering(split, segment.split_by)
    rating[1] += _crossings_for_ordering(segment.split_by, partner)
    return rating


def _better(area, rating, best_area, best_rating):
    return (rating[1] < best_rating[1]
            or (rating[1] == best_rating[1] and
                (rating[0] < best_rating[0] or (rating[0] == best_rating[0] and area.size > best_area.size))))


def _choose_area(segment, areas, first, last):
    best = first
    if first < last:
        split, partner = _Segment(), _Segment()
        split.incoming.extend(segment.incoming)
        split.split_by = segment.split_by
        split.split_partner = partner
        _extent(split)
        partner.outgoing.extend(segment.outgoing)
        partner.split_partner = split
        _extent(partner)
        best_rating = _rate_area(segment, split, partner, areas[best])
        for index in range(first + 1, last + 1):
            rating = _rate_area(segment, split, partner, areas[index])
            if _better(areas[index], rating, areas[best], best_rating):
                best, best_rating = index, rating
    return best


def _use_area(areas, index, threshold):
    area = areas.pop(index)
    if area.size / 2 >= threshold:
        insert = index
        center = area.center
        end = center - threshold
        if area.start <= center - threshold:
            areas.insert(insert, _Area(area.start, end))
            insert += 1
        start = center + threshold
        if start <= area.end:
            areas.insert(insert, _Area(start, area.end))


def _split_position(segment, areas, threshold):
    first, last = -1, -1
    for index, area in enumerate(areas):
        if area.start > segment.end:
            break
        if area.end >= segment.start:
            if first < 0:
                first = index
            last = index
    position = (segment.start + segment.end) / 2
    if first >= 0:
        chosen = _choose_area(segment, areas, first, last)
        position = areas[chosen].center
        _use_area(areas, chosen, threshold)
    return position


def _split_at(segment, position):
    partner = _Segment()
    segment.split_partner = partner
    partner.split_partner = segment
    partner.outgoing.extend(segment.outgoing)
    segment.outgoing.clear()
    segment.outgoing.append(position)
    partner.incoming.append(position)
    _extent(segment)
    _extent(partner)
    while segment.incoming_dependencies:
        _remove_dependency(segment.incoming_dependencies[0])
    while segment.outgoing_dependencies:
        _remove_dependency(segment.outgoing_dependencies[0])
    return partner


class _Generator:
    def __init__(self, edge_spacing):
        self.edge_spacing = edge_spacing
        self.conflict_threshold = 0.5 * edge_spacing
        self.critical_threshold = 0.0
        self.created_junctions = _CoordinateSet()

    def _conflicts(self, first, second):
        conflicts = 0
        if first and second:
            a, b = 0, 0
            while True:
                one, two = first[a], second[b]
                if one > two - self.critical_threshold and one < two + self.critical_threshold:
                    return -1
                if one > two - self.conflict_threshold and one < two + self.conflict_threshold:
                    conflicts += 1
                if one <= two and a + 1 < len(first):
                    a += 1
                elif two <= one and b + 1 < len(second):
                    b += 1
                else:
                    break
        return conflicts

    def _create_dependency(self, first, second):
        if abs(first.start - first.end) < EPSILON or abs(second.start - second.end) < EPSILON:
            return 0
        conflicts_one = self._conflicts(first.outgoing, second.incoming)
        conflicts_two = self._conflicts(second.outgoing, first.incoming)
        critical_count = 0
        if conflicts_one == -1 or conflicts_two == -1:
            if conflicts_one == -1:
                _dependency("CRITICAL", second, first, 1)
                critical_count += 1
            if conflicts_two == -1:
                _dependency("CRITICAL", first, second, 1)
                critical_count += 1
        else:
            crossings_one = _crossings_for_ordering(first, second)
            crossings_two = _crossings_for_ordering(second, first)
            value_one = conflicts_one + 16 * crossings_one
            value_two = conflicts_two + 16 * crossings_two
            if value_one < value_two:
                _dependency("REGULAR", first, second, value_two - value_one)
            elif value_one > value_two:
                _dependency("REGULAR", second, first, value_one - value_two)
            elif value_one > 0 and value_two > 0:
                _dependency("REGULAR", first, second, 0)
                _dependency("REGULAR", second, first, 0)
        return critical_count

    def _update_dependencies(self, segment, segments):
        causing, partner = segment.split_by, segment.split_partner
        _dependency("CRITICAL", segment, causing, 1)
        _dependency("CRITICAL", causing, partner, 1)
        for other in segments:
            if other is not causing and other is not segment and other is not partner:
                self._create_dependency(other, segment)
                self._create_dependency(other, partner)

    def _split_segments(self, dependencies, segments):
        if not dependencies:
            return
        coordinates = sorted((value for segment in segments for values in (segment.incoming, segment.outgoing) for value in values),
                             key=cmp_to_key(_compare_double))
        areas = [_Area(coordinates[index - 1] + self.critical_threshold, coordinates[index] - self.critical_threshold)
                 for index in range(1, len(coordinates))
                 if coordinates[index] - coordinates[index - 1] >= 2 * self.critical_threshold]
        selected = []
        for dependency in dependencies:
            source, target = dependency.source, dependency.target
            if source in selected or target in selected:
                continue
            chosen, causing = source, target
            if len(source.incoming) + len(source.outgoing) > 2 and len(target.incoming) + len(target.outgoing) <= 2:
                chosen, causing = target, source
            selected.append(chosen)
            chosen.split_by = causing
        selected.sort(key=cmp_to_key(lambda a, b: _compare_double(a.end - a.start, b.end - b.start)))
        for segment in selected:
            position = _split_position(segment, areas, self.critical_threshold)
            segments.append(_split_at(segment, position))
            self._update_dependencies(segment, segments)

    def _junction(self, edge, segment, position):
        key = (position.x, position.y)
        if key in self.created_junctions:
            return
        p = position.y
        inside = p > segment.start and p < segment.end
        boundary = False
        if segment.incoming and segment.outgoing:
            boundary = ((abs(p - segment.incoming[0]) < EPSILON and abs(p - segment.outgoing[0]) < EPSILON)
                        or (abs(p - segment.incoming[-1]) < EPSILON and abs(p - segment.outgoing[-1]) < EPSILON))
        if inside or boundary:
            point = Vec2(position.x, position.y)
            get_junction_points(edge).append(point)
            self.created_junctions.add(key)

    def _bends(self, segment, start_position):
        if segment.split_partner is not None and segment.split_by is None:
            return
        segment_x = start_position + segment.slot * self.edge_spacing
        for port in segment.ports:
            source_y = _vector_sum_y(port)
            for edge in port.outgoing_edges:
                if edge.source.owner is edge.target.owner:
                    continue
                target_y = _vector_sum_y(edge.target)
                if abs(source_y - target_y) > EPSILON:
                    current_x, current = segment_x, segment
                    point = Vec2(current_x, source_y)
                    edge.bend_points.append(point)
                    self._junction(edge, current, point)
                    partner = segment.split_partner
                    if partner is not None:
                        split_y = partner.incoming[0]
                        point = Vec2(current_x, split_y)
                        edge.bend_points.append(point)
                        self._junction(edge, current, point)
                        current_x = start_position + partner.slot * self.edge_spacing
                        current = partner
                        point = Vec2(current_x, split_y)
                        edge.bend_points.append(point)
                        self._junction(edge, current, point)
                    point = Vec2(current_x, target_y)
                    edge.bend_points.append(point)
                    self._junction(edge, current, point)

    def route(self, graph, source_nodes, target_nodes, start_position):
        segments, mapping = [], _IdentityMap(graph)
        _create_segments(source_nodes, "EAST", segments, mapping)
        _create_segments(target_nodes, "WEST", segments, mapping)
        incoming = _minimum_difference(value for segment in segments for value in segment.incoming)
        outgoing = _minimum_difference(value for segment in segments for value in segment.outgoing)
        self.critical_threshold = 0.2 * _minimum(incoming, outgoing)
        critical = 0
        for first in range(len(segments) - 1):
            for second in range(first + 1, len(segments)):
                critical += self._create_dependency(segments[first], segments[second])
        random = graph.properties.get("RANDOM")
        if critical >= 2:
            self._split_segments(_detect_cycles(segments, True, random), segments)
        _break_cycles(segments, random)
        _number_slots(segments)
        rank = -1
        for segment in segments:
            if abs(segment.start - segment.end) < EPSILON:
                continue
            rank = max(rank, segment.slot)
            self._bends(segment, start_position)
        self.created_junctions.clear()
        return rank + 1


def _place_nodes_horizontally(layer, offset):
    left = right = 0.0
    for node in layer.nodes:
        left = _maximum(left, node.margin.left)
        right = _maximum(right, node.margin.right)
    for node in layer.nodes:
        alignment = read_layered_scalar(node, 'ALIGNMENT', 'ALIGNMENT')
        if alignment == 'LEFT':
            ratio = 0.0
        elif alignment == 'RIGHT':
            ratio = 1.0
        elif alignment == 'CENTER':
            ratio = 0.5
        else:
            inputs = sum(bool(port.incoming_edges)for port in node.ports)
            outputs = sum(bool(port.outgoing_edges)for port in node.ports)
            ratio = outputs / (inputs + outputs)if inputs + outputs else 0.5
        width = node.size.x
        position = (layer.size.x - width) * ratio
        if ratio > 0.5:
            position -= right * 2 * (ratio - 0.5)
        elif ratio < 0.5:
            position += left * 2 * (0.5 - ratio)
        if position < node.margin.left:
            position = node.margin.left
        if position > layer.size.x - node.margin.right - width:
            position = layer.size.x - node.margin.right - width
        node.pos.x = offset + position


def _is_external_west_or_east(node):
    # Source reads the actual property before checking the node's type.
    side = node.properties.get('EXT_PORT_SIDE')
    return node.type == 'EXTERNAL_PORT'and side in ('WEST', 'EAST')


def orthogonal_edge_router(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Orthogonal edge routing', 1)
    node_spacing = read_layered_scalar(graph, 'SPACING_NODE_NODE_BETWEEN_LAYERS',
                                       'SPACING_NODE_NODE_BETWEEN_LAYERS_0')
    edge_spacing = read_layered_scalar(graph, 'SPACING_EDGE_EDGE_BETWEEN_LAYERS',
                                       'SPACING_EDGE_EDGE_BETWEEN_LAYERS_0')
    edge_node_spacing = read_layered_scalar(graph, 'SPACING_EDGE_NODE_BETWEEN_LAYERS',
                                            'SPACING_EDGE_NODE_BETWEEN_LAYERS_0')
    generator = _Generator(edge_spacing)
    x_position = 0.0
    left = None
    for right in [*graph.layers, None]:
        left_nodes = left.nodes if left is not None else None
        right_nodes = right.nodes if right is not None else None
        if left is not None:
            _place_nodes_horizontally(left, x_position)
            x_position += left.size.x
        start_position = x_position if left is None else x_position + edge_node_spacing
        slots = generator.route(graph, left_nodes, right_nodes, start_position)
        left_external = left is None or all(_is_external_west_or_east(node)for node in left_nodes)
        right_external = right is None or all(_is_external_west_or_east(node)for node in right_nodes)
        if slots > 0:
            width = (slots - 1) * edge_spacing
            if left is not None:
                width += edge_node_spacing
            if right is not None:
                width += edge_node_spacing
            if width < node_spacing and not left_external and not right_external:
                width = node_spacing
            x_position += width
        elif not left_external and not right_external:
            x_position += node_spacing
        left = right
    graph.size.x = x_position
    monitor.done()


