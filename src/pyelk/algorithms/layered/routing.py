# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Port of elkjs 0.12.1 generated lib/elk-worker.js, RIGHT orthogonal routing.
# Commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source/guards: references/e05-source-routing.json; E05 component approvals.
# E06 work/NORTH/scale guards: references/e06-source-components-R.json; NOTICE-E06.md.
# Exact external Java build unresolved. See pyelk/_licenses/NOTICE-E05.md.
"""Source routing segments, dependencies and critical-cycle splitting.

Only the reviewed flat RIGHT implicit-port work graph is admitted. The source
0.001 routing threshold is retained; it does not change comparison tolerances.
No reference, oracle, case identifier or external engine is read here.
"""
from collections import deque
from dataclasses import dataclass, field
from functools import cmp_to_key
import math

from ..._errors import UnsupportedFeatureError
from .graph import LGraph, Vec2
from .long_edges import get_junction_points

EPSILON = 0.001
DOUBLE_MAX = 1.7976931348623157e308
_P = "org.eclipse.elk."


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PHASE_INPUT", "", message)


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
        difference = min(difference, numbers[index] - numbers[index - 1])
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
            segment.start = values[0] if math.isnan(segment.start) else min(segment.start, values[0])
            segment.end = values[-1] if math.isnan(segment.end) else max(segment.end, values[-1])


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
    mapping[port] = segment
    segment.ports.append(port)
    values = segment.incoming if port.side == "EAST" else segment.outgoing
    _insert_sorted(values, _port_y(port))
    _extent(segment)
    for edge in port.incoming_edges:
        other = edge.source
        if other not in mapping:
            _add_port_positions(segment, other, mapping)
    for edge in port.outgoing_edges:
        other = edge.target
        if other not in mapping:
            _add_port_positions(segment, other, mapping)


def _create_segments(nodes, side, segments, mapping):
    if nodes is None:
        return
    for node in nodes:
        # Source getPorts_0 uses ordered side/type predicates, not side caches.
        for port in node.ports:
            if port.side == side and port.outgoing_edges and port not in mapping:
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
        segment.critical_in_weight = sum(d.weight for d in segment.incoming_dependencies if d.kind == "CRITICAL")
        segment.critical_out_weight = sum(d.weight for d in segment.outgoing_dependencies if d.kind == "CRITICAL")
        segment.in_weight = (segment.critical_in_weight if critical_only
                             else sum(d.weight for d in segment.incoming_dependencies))
        segment.out_weight = (segment.critical_out_weight if critical_only
                              else sum(d.weight for d in segment.outgoing_dependencies))
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
        self.created_junctions = set()

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
        segments, mapping = [], {}
        _create_segments(source_nodes, "EAST", segments, mapping)
        _create_segments(target_nodes, "WEST", segments, mapping)
        incoming = _minimum_difference(value for segment in segments for value in segment.incoming)
        outgoing = _minimum_difference(value for segment in segments for value in segment.outgoing)
        self.critical_threshold = 0.2 * min(incoming, outgoing)
        critical = 0
        for first in range(len(segments) - 1):
            for second in range(first + 1, len(segments)):
                critical += self._create_dependency(segments[first], segments[second])
        if critical >= 2:
            self._split_segments(_detect_cycles(segments, True, graph.random), segments)
        _break_cycles(segments, graph.random)
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
    left = max([0.0, *[node.margin.left for node in layer.nodes]])
    right = max([0.0, *[node.margin.right for node in layer.nodes]])
    for node in layer.nodes:
        inputs = sum(bool(port.incoming_edges) for port in node.ports)
        outputs = sum(bool(port.outgoing_edges) for port in node.ports)
        ratio = outputs / (inputs + outputs) if inputs + outputs else 0.5
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


def _admit(graph):
    if not isinstance(graph, LGraph) or graph.layerless_nodes or len(graph.layers) > 8:
        _outside("Routing requires the reviewed layered work graph")
    nodes = [node for layer in graph.layers for node in layer.nodes]
    if len(nodes) > 176 or len(set(nodes)) != len(nodes) or sum(node.type == "NORMAL" for node in nodes) > 8:
        _outside("E05 routing work-node bounds or identity differ")
    layers = {layer: index for index, layer in enumerate(graph.layers)}
    edges = set()
    for layer in graph.layers:
        if (layer.graph is not graph or type(layer.size.x) not in (int, float)
                or not 0 <= layer.size.x <= 1_000_000_000 or not math.isfinite(layer.size.x)):
            _outside("Layer ownership or width cache differs")
        for node in layer.nodes:
            if node.graph is not graph or node.layer is not layer or node.type not in ("NORMAL", "LONG_EDGE"):
                _outside("Node type or layer ownership is outside E05")
            constraints = node.properties.get("PORT_CONSTRAINTS")
            if constraints not in (("FIXED_POS",) if node.type == "LONG_EDGE" else ("FIXED_SIDE", "FIXED_ORDER")):
                _outside("Port constraints require the real predecessor processors")
            if "ALIGNMENT" in node.properties and node.properties["ALIGNMENT"] not in (None, "UNDEFINED"):
                _outside("Explicit node alignment is outside the approved slice")
            for value in (node.size.x, node.size.y, node.margin.left, node.margin.right, node.margin.top, node.margin.bottom):
                if type(value) not in (int, float) or not 0 <= value <= 1_000_000 or not math.isfinite(value):
                    _outside("Nonfinite or unreviewed node geometry")
            if layer.size.x < node.size.x:
                _outside("Required layer-width processor has not run")
            for value in (node.pos.x, node.pos.y):
                if type(value) not in (int, float) or abs(value) > 1_000_000_000 or not math.isfinite(value):
                    _outside("Nonfinite or unreviewed internal positions")
            for port in node.ports:
                if port.owner is not node:
                    _outside("Only implicit single-edge ports are reviewed")
                if any(type(v) not in (int, float) or v != 0 for v in (port.size.x, port.size.y, port.anchor.x, port.anchor.y)):
                    _outside("Explicit port size/anchor is outside E05")
                if not all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 1_000_000_000 for v in (port.pos.x, port.pos.y)):
                    _outside("Nonfinite or unreviewed port positions")
                if port.side == "NORTH" and not port.incoming_edges and not port.outgoing_edges:
                    continue  # The source E/W side filters ignore detached loops.
                if len(port.incoming_edges) + len(port.outgoing_edges) != 1:
                    _outside("Every live implicit port must have one flow segment")
                if (port.outgoing_edges and port.side != "EAST") or (port.incoming_edges and port.side != "WEST"):
                    _outside("Only source EAST and target WEST ports are reviewed")
                for edge in port.incoming_edges + port.outgoing_edges:
                    if edge.source is None or edge.target is None or edge.source.owner is edge.target.owner:
                        _outside("Detached or self edge is outside E05")
                    if edge.source.owner.layer not in layers or edge.target.owner.layer not in layers:
                        _outside("Routing endpoint is outside the layered graph")
                    if layers[edge.target.owner.layer] != layers[edge.source.owner.layer] + 1:
                        _outside("Long-edge splitting must precede routing")
                    if edge.source.outgoing_edges != [edge] or edge.target.incoming_edges != [edge]:
                        _outside("Ordered source/target adjacency is inconsistent")
                    edges.add(edge)
    if len(edges) > 196 or sum(len(node.ports) for node in nodes) > 392:
        _outside("Routing work-edge or port bounds exceed the reviewed domain")
    if edges and graph.random is None:
        _outside("Routing requires the real per-call generated random stream")


def orthogonal_edge_router(graph):
    """Source process84 with full WestToEast segment routing and cycle handling."""
    _admit(graph)
    try:
        node_spacing = graph.options.values[_P + "layered.spacing.nodeNodeBetweenLayers"]
    except (AttributeError, KeyError, TypeError):
        _outside("Routing requires resolved spacing options")
    if type(node_spacing) not in (int, float) or not 0 <= node_spacing <= 1_000_000 or not math.isfinite(node_spacing):
        _outside("Routing spacing is outside the reviewed numeric domain")
    # These two private options remain at their exact fixed-source defaults.
    edge_spacing, edge_node_spacing = 10.0, 10.0
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
        # External nodes are excluded by admission; empty boundaries still
        # use the actual all(empty) predicate, as in the generated source.
        left_external = left is None or all(node.type == "EXTERNAL_PORT" for node in left_nodes)
        right_external = right is None or all(node.type == "EXTERNAL_PORT" for node in right_nodes)
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
