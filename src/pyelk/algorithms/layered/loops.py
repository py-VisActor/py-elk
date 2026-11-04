# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Port of elkjs 0.12.1 generated lib/elk-worker.js, default implicit self-loops.
# Commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source/guards: references/e06-source-components-B.json; E06 component approvals.
# Exact external Java build unresolved. See pyelk/_licenses/NOTICE-E06.md.
"""Ordered private self-loop holders and the reviewed default processors.

Only independently allocated implicit ports, NORTH distribution and STACKED
ordering are admitted. References/oracle files are never read at runtime.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math

from ..._errors import UnsupportedFeatureError
from .graph import LEdge, LGraph, LNode, LPort, Vec2, set_port_owner, set_source, set_target

_SIDES = ("UNDEFINED", "NORTH", "EAST", "SOUTH", "WEST")


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PHASE_INPUT", "", message)


@dataclass(eq=False)
class SelfLoopPort:
    port: LPort
    incoming: list[SelfLoopEdge] = field(default_factory=list)
    outgoing: list[SelfLoopEdge] = field(default_factory=list)
    had_only_self_loops: bool = False
    is_hidden: bool = False


@dataclass(eq=False)
class SelfLoopEdge:
    edge: LEdge
    source: SelfLoopPort
    target: SelfLoopPort
    loop: SelfHyperLoop | None = None


@dataclass(eq=False)
class SelfHyperLoop:
    holder: SelfLoopHolder
    ports: list[SelfLoopPort] = field(default_factory=list)
    # Identity-set semantics; the admitted implicit component has one edge.
    edges: list[SelfLoopEdge] = field(default_factory=list)
    ports_by_side: dict[str, list[SelfLoopPort]] = field(default_factory=dict)
    occupied_sides: list[str] = field(default_factory=list)
    routing_slot: list[int] = field(default_factory=lambda: [0] * 5)
    self_loop_type: str | None = None
    leftmost_port: SelfLoopPort | None = None
    rightmost_port: SelfLoopPort | None = None
    labels: None = None


@dataclass(eq=False)
class SelfLoopHolder:
    node: LNode
    loops: list[SelfHyperLoop] = field(default_factory=list)
    ports: dict[LPort, SelfLoopPort] = field(default_factory=dict)
    routing_slot_count: list[int] = field(default_factory=lambda: [0] * 5)
    are_ports_hidden: bool = False


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _nodes(graph, *, layered):
    if not isinstance(graph, LGraph):
        _outside("A prepared layered graph is required")
    if layered:
        if graph.layerless_nodes or len(graph.layers) > 8:
            _outside("The self-loop stage requires prepared layers")
        nodes = [node for layer in graph.layers for node in layer.nodes]
        if any(layer.graph is not graph or any(node.layer is not layer for node in layer.nodes)
               for layer in graph.layers):
            _outside("Layer membership is inconsistent")
    else:
        if graph.layers:
            _outside("Self-loop preprocessing precedes layering")
        nodes = list(graph.layerless_nodes)
    if len(nodes) > (176 if layered else 8) or len(set(nodes)) != len(nodes):
        _outside("The reviewed node bound or uniqueness is violated")
    if sum(node.type == "NORMAL" for node in nodes) > 8:
        _outside("At most eight original nodes are reviewed")
    ports = set()
    for node in nodes:
        if (not isinstance(node, LNode) or node.graph is not graph
                or node.type not in (("NORMAL", "LONG_EDGE") if layered else ("NORMAL",))
                or not all(_finite(v) and 0 <= v <= 1_000_000 for v in (node.size.x, node.size.y))):
            _outside("The node is outside the reviewed self-loop domain")
        for port in node.ports:
            if not isinstance(port, LPort) or port.owner is not node or port in ports:
                _outside("Port ownership or uniqueness is inconsistent")
            ports.add(port)
    if len(ports) > 392:
        _outside("The reviewed port bound is exceeded")
    return nodes


def _self_loop(edge):
    return edge.source is not None and edge.target is not None and edge.source.owner is edge.target.owner


def _validate_before_pre(graph):
    nodes = _nodes(graph, layered=False)
    node_set = set(nodes)
    edges = set()
    for node in nodes:
        if "SELF_LOOP_HOLDER" in node.properties:
            _outside("Preprocessing requires fresh holders")
        for port in node.ports:
            if (port.side not in ("EAST", "WEST") or port.origin is not None
                    or port.size.x != 0 or port.size.y != 0
                    or len(port.incoming_edges) + len(port.outgoing_edges) != 1):
                _outside("Only independent implicit one-edge ports are reviewed")
            for edge in [*port.incoming_edges, *port.outgoing_edges]:
                if (not isinstance(edge, LEdge) or edge.source is None or edge.target is None
                        or edge.source.owner not in node_set or edge.target.owner not in node_set
                        or edge.source.outgoing_edges.count(edge) != 1
                        or edge.target.incoming_edges.count(edge) != 1
                        or (edge.source is not port and edge.target is not port)):
                    _outside("The original edge adjacency is inconsistent")
                edges.add(edge)
    if len(edges) > 28:
        _outside("At most twenty-eight original edges are reviewed")
    for node in nodes:
        if any(_self_loop(edge) for port in node.ports for edge in port.outgoing_edges):
            if (node.properties.get("PORT_CONSTRAINTS") != "FREE"
                    or node.properties.get("ORIGINAL_PORT_CONSTRAINTS") != "FREE"):
                _outside("Only default FREE original loop ports are reviewed")
    return nodes


def _wrapper_port(holder, port):
    if port not in holder.ports:
        connected = [*port.incoming_edges, *port.outgoing_edges]
        holder.ports[port] = SelfLoopPort(port, had_only_self_loops=all(_self_loop(e) for e in connected))
    return holder.ports[port]


def _add_loop_edge(loop, edge):
    if edge in loop.edges:
        return
    loop.edges.append(edge)
    edge.loop = loop
    if edge.source not in loop.ports:
        loop.ports.append(edge.source)
    if edge.target not in loop.ports:
        loop.ports.append(edge.target)


def _initialize_holder(holder):
    # Canonical $initialize_3/$initializeHyperLoop preserve outgoing traversal,
    # LinkedHashMap insertion and BFS outgoing-before-incoming order.
    for port in holder.node.ports:
        for edge in port.outgoing_edges:
            if _self_loop(edge):
                source, target = _wrapper_port(holder, edge.source), _wrapper_port(holder, edge.target)
                wrapped = SelfLoopEdge(edge, source, target)
                source.outgoing.append(wrapped)
                target.incoming.append(wrapped)
    for wrapped in holder.ports.values():
        wrapped.port.id = 0
    for wrapped in holder.ports.values():
        if wrapped.port.id != 0:
            continue
        loop = SelfHyperLoop(holder)
        queue = deque([wrapped])
        while queue:
            current = queue.popleft()
            current.port.id = 1
            for edge in current.outgoing:
                _add_loop_edge(loop, edge)
                if edge.target.port.id == 0:
                    queue.append(edge.target)
            for edge in current.incoming:
                _add_loop_edge(loop, edge)
                if edge.source.port.id == 0:
                    queue.append(edge.source)
        holder.loops.append(loop)


def self_loop_pre_processor(graph):
    """Canonical $process_49: capture, detach edges, then hide original ports."""
    nodes = _validate_before_pre(graph)
    for node in nodes:
        if not any(_self_loop(e) for p in node.ports for e in p.outgoing_edges):
            continue
        holder = SelfLoopHolder(node)
        node.properties["SELF_LOOP_HOLDER"] = holder
        _initialize_holder(holder)
        for loop in holder.loops:
            for wrapped in loop.edges:
                set_source(wrapped.edge, None)
                set_target(wrapped.edge, None)
        for wrapped in holder.ports.values():
            if wrapped.had_only_self_loops:
                set_port_owner(wrapped.port, None)
                wrapped.is_hidden = True
                holder.are_ports_hidden = True


def _holders(graph):
    nodes = _nodes(graph, layered=True)
    result = []
    for node in nodes:
        if node.type != "NORMAL" or "SELF_LOOP_HOLDER" not in node.properties:
            continue
        holder = node.properties["SELF_LOOP_HOLDER"]
        if (not isinstance(holder, SelfLoopHolder) or holder.node is not node
                or not 1 <= len(holder.loops) <= 28
                or node.properties.get("ORIGINAL_PORT_CONSTRAINTS") != "FREE"
                or len(holder.routing_slot_count) != 5):
            _outside("A default implicit self-loop holder is required")
        seen = set()
        for loop in holder.loops:
            if (not isinstance(loop, SelfHyperLoop) or loop.holder is not holder
                    or len(loop.ports) != 2 or len(loop.edges) != 1 or loop.labels is not None
                    or len(loop.routing_slot) != 5):
                _outside("Only one-edge, two-port, unlabelled loops are reviewed")
            wrapped = loop.edges[0]
            if (not isinstance(wrapped, SelfLoopEdge) or wrapped.loop is not loop
                    or not isinstance(wrapped.edge, LEdge)
                    or wrapped.source is wrapped.target
                    or set(loop.ports) != {wrapped.source, wrapped.target}
                    or wrapped.source.incoming or wrapped.source.outgoing != [wrapped]
                    or wrapped.target.incoming != [wrapped] or wrapped.target.outgoing):
                _outside("Self-loop wrapper relationships are inconsistent")
            for port_wrapper in loop.ports:
                port = port_wrapper.port
                if (port in seen or holder.ports.get(port) is not port_wrapper
                        or not port_wrapper.had_only_self_loops
                        or port.origin is not None or port.size.x != 0 or port.size.y != 0):
                    _outside("Self-loop ports must be distinct implicit ports")
                seen.add(port)
        if seen != set(holder.ports):
            _outside("The holder port map is inconsistent")
        if len(node.ports) + (len(holder.ports) if holder.are_ports_hidden else 0) > 56:
            _outside("The original endpoint-port bound is exceeded")
        result.append(holder)
    if sum(len(holder.loops) for holder in result) > 28:
        _outside("At most twenty-eight original self-loop edges are reviewed")
    return result


def _compute_ports_per_side(loop):
    if any(port.port.side != "NORTH" for port in loop.ports):
        _outside("The reviewed default distribution is NORTH")
    # Source replaces the multimap on every call, in actual slPorts order.
    loop.ports_by_side = {"NORTH": list(loop.ports)}
    loop.self_loop_type = "ONE_SIDE"


def _net_flow(port):
    return len(port.incoming) - len(port.outgoing)


def _split_index(ports):
    # Literal generated $computePortListSplitIndex, including its second >0.
    positive = 0
    while positive < len(ports) and _net_flow(ports[positive]) <= 0:
        positive += 1
    if positive > 0 and positive < len(ports) - 1:
        return positive
    non_negative = 0
    while non_negative < len(ports) and _net_flow(ports[non_negative]) <= 0:
        non_negative += 1
    if non_negative > 0 and positive < len(ports) - 1:
        return non_negative
    return len(ports) // 2


def _restore_ports(holder):
    areas = {(side, area): [] for side in _SIDES for area in ("START", "MIDDLE", "END")}
    for loop in holder.loops:
        sorted_ports = sorted(loop.ports, key=_net_flow)
        split = _split_index(sorted_ports)
        first = [port for port in sorted_ports[:split] if port.is_hidden]
        first.reverse()
        second = [port for port in sorted_ports[split:] if port.is_hidden]
        second.reverse()
        areas["NORTH", "MIDDLE"][0:0] = first
        areas["NORTH", "MIDDLE"].extend(second)
    node, old = holder.node, list(holder.node.ports)
    node.ports.clear()
    index = 0

    def add(side, area):
        for wrapped in areas[side, area]:
            set_port_owner(wrapped.port, node)

    def old_that(predicate):
        nonlocal index
        while index < len(old) and predicate(old[index]):
            node.ports.append(old[index])
            index += 1

    # Source $restorePorts ordering; nonloop N/S connections are guarded out.
    add("NORTH", "START")
    old_that(lambda port: False)
    add("NORTH", "MIDDLE")
    old_that(lambda port: port.side == "NORTH")
    add("NORTH", "END")
    add("EAST", "START")
    add("EAST", "MIDDLE")
    old_that(lambda port: port.side == "EAST")
    add("EAST", "END")
    add("SOUTH", "START")
    old_that(lambda port: False)
    add("SOUTH", "MIDDLE")
    old_that(lambda port: port.side == "SOUTH")
    add("SOUTH", "END")
    add("WEST", "START")
    old_that(lambda port: port.side == "WEST")
    add("WEST", "MIDDLE")
    add("WEST", "END")
    for side in _SIDES:
        for area in ("START", "MIDDLE", "END"):
            for wrapped in areas[side, area]:
                wrapped.is_hidden = False
    holder.are_ports_hidden = False


def self_loop_port_restorer(graph):
    """Canonical $process_47 default NORTH/STACKED branch."""
    holders = _holders(graph)
    for holder in holders:
        for wrapped in holder.ports.values():
            if holder.are_ports_hidden:
                if (not wrapped.is_hidden or wrapped.port.owner is not None
                        or wrapped.port.incoming_edges or wrapped.port.outgoing_edges):
                    _outside("Loop ports were not independently hidden")
            elif wrapped.port.owner is not holder.node or wrapped.port.side != "NORTH":
                _outside("Restored loop ports are inconsistent")
        if holder.are_ports_hidden and any(p.side not in ("EAST", "WEST") for p in holder.node.ports):
            _outside("Only ordinary E/W ports may remain during crossing")
        if holder.are_ports_hidden and [p.side for p in holder.node.ports] != sorted(
                (p.side for p in holder.node.ports), key=("EAST", "WEST").index):
            _outside("The source sorted E/W port groups are not prepared")
    for holder in holders:
        if holder.are_ports_hidden:
            for loop in holder.loops:
                for wrapped in loop.ports:
                    if wrapped.is_hidden:
                        wrapped.port.side = "NORTH"
                        wrapped.port.anchor.x = wrapped.port.size.x / 2
                        wrapped.port.anchor.y = 0
        for loop in holder.loops:
            _compute_ports_per_side(loop)
        if holder.are_ports_hidden:
            _restore_ports(holder)


def self_loop_post_processor(graph):
    """Canonical $process_48/$restoreEdge: reconnect then translate bends."""
    holders = _holders(graph)
    for holder in holders:
        if holder.are_ports_hidden or not all(_finite(v) for v in (holder.node.pos.x, holder.node.pos.y)):
            _outside("Loop postprocessing requires restored ports and positioned nodes")
        for loop in holder.loops:
            for wrapped in loop.edges:
                if (wrapped.source.port.owner is not holder.node or wrapped.target.port.owner is not holder.node
                        or any(not _finite(v) for p in wrapped.edge.bend_points for v in (p.x, p.y))):
                    _outside("The routed loop or its original ports are invalid")
    for holder in holders:
        for loop in holder.loops:
            for wrapped in loop.edges:
                set_source(wrapped.edge, wrapped.source.port)
                set_target(wrapped.edge, wrapped.target.port)
                for point in wrapped.edge.bend_points:
                    point.x += holder.node.pos.x
                    point.y += holder.node.pos.y


@dataclass(eq=False)
class _LoopSegment:
    incoming: list[_LoopDependency] = field(default_factory=list)
    outgoing: list[_LoopDependency] = field(default_factory=list)
    mark: int = 0
    in_weight: int = 0
    out_weight: int = 0
    critical_in_weight: int = 0
    critical_out_weight: int = 0
    slot: int = 0


@dataclass(eq=False)
class _LoopDependency:
    source: _LoopSegment
    target: _LoopSegment
    weight: int
    kind: str = "REGULAR"


def _dependency(source, target, weight):
    dependency = _LoopDependency(source, target, weight)
    source.outgoing.append(dependency)
    target.incoming.append(dependency)


def _update_neighbors(node, sources, sinks):
    for dependency in node.outgoing:
        target = dependency.target
        if target.mark < 0 and dependency.weight > 0:
            target.in_weight -= dependency.weight
            if dependency.kind == "CRITICAL":
                target.critical_in_weight -= dependency.weight
            if target.in_weight <= 0 and target.out_weight > 0:
                sources.append(target)
    for dependency in node.incoming:
        source = dependency.source
        if source.mark < 0 and dependency.weight > 0:
            source.out_weight -= dependency.weight
            if dependency.kind == "CRITICAL":
                source.critical_out_weight -= dependency.weight
            if source.out_weight <= 0 and source.in_weight > 0:
                sinks.append(source)


def _detect_nested_cycles(segments):
    """Actual initialize/weighted queue/mark path; random chooser guarded out.

    The validated NORTH STACKED intervals induce strictly outer-to-inner
    positive dependencies. Source TreeSet membership is represented in natural
    mark order; each object is removed before its key changes. Its nonempty
    fallback traversal and RNG chooser are unreachable under this proof.
    """
    sources, sinks = deque(), deque()
    for index, segment in enumerate(segments):
        segment.mark = -index - 1
        segment.critical_in_weight = sum(d.weight for d in segment.incoming if d.kind == "CRITICAL")
        segment.critical_out_weight = sum(d.weight for d in segment.outgoing if d.kind == "CRITICAL")
        segment.in_weight = sum(d.weight for d in segment.incoming)
        segment.out_weight = sum(d.weight for d in segment.outgoing)
        if segment.out_weight == 0:
            sinks.append(segment)
        elif segment.in_weight == 0:
            sources.append(segment)
    unprocessed = sorted(segments, key=lambda segment: segment.mark)
    mark_base = len(segments)
    next_sink, next_source = mark_base - 1, mark_base + 1
    while unprocessed:
        while sinks:
            sink = sinks.popleft()
            unprocessed.remove(sink)
            sink.mark = next_sink
            next_sink -= 1
            _update_neighbors(sink, sources, sinks)
        while sources:
            source = sources.popleft()
            unprocessed.remove(source)
            source.mark = next_source
            next_source += 1
            _update_neighbors(source, sources, sinks)
        if unprocessed:
            raise RuntimeError("Validated nested loop dependencies did not drain")
    for segment in segments:
        if segment.mark < mark_base:
            segment.mark += len(segments) + 1
    # Canonical detectCycles/breakNonCriticalCycles iteration is retained; the
    # source guard proves this list empty, with no dependency reversal/removal.
    cycles = [d for segment in segments for d in segment.outgoing if segment.mark > d.target.mark]
    if cycles:
        raise RuntimeError("Validated nested loops unexpectedly contain a directed cycle")


def _set_slot(loop, side, slot):
    index = _SIDES.index(side)
    loop.routing_slot[index] = slot
    loop.holder.routing_slot_count[index] = max(loop.holder.routing_slot_count[index], slot + 1)


def _activity(holder):
    activities = {}
    count = len(holder.node.ports)
    for loop in holder.loops:
        values = [False] * count
        index = loop.leftmost_port.port.id - 1
        target = loop.rightmost_port.port.id
        while index != target:
            index = (index + 1) % count
            values[index] = True
        activities[loop] = values
    return activities


def _assign_slots(holder):
    # No labels -> actual source matrix0x0. Each source segment/dependency and
    # activity array is still constructed; no loop-index answer substitution.
    label_crossings = []
    segments = [_LoopSegment() for _ in holder.loops]
    loop_segments = dict(zip(holder.loops, segments))
    activities = _activity(holder)
    for first_index, first in enumerate(holder.loops[:-1]):
        for second in holder.loops[first_index + 1:]:
            first_above = sum(activities[second][port.port.id] for port in first.ports)
            second_above = sum(activities[first][port.port.id] for port in second.ports)
            if first_above < second_above:
                _dependency(loop_segments[first], loop_segments[second], second_above - first_above)
            elif second_above < first_above:
                _dependency(loop_segments[second], loop_segments[first], first_above - second_above)
            elif first_above != 0:
                # Rejected by the complete preflight nested-interval guard.
                raise RuntimeError("Validated default loop intervals are not nested")
    _detect_nested_cycles(segments)
    sinks = deque()
    for segment in segments:
        segment.in_weight = len(segment.incoming)
        segment.out_weight = len(segment.outgoing)
        if segment.out_weight == 0:
            segment.slot = 0
            sinks.append(segment)
    while sinks:
        segment = sinks.popleft()
        next_slot = segment.slot + 1
        for dependency in segment.incoming:
            source = dependency.source
            source.slot = max(source.slot, next_slot)
            source.out_weight -= 1
            if source.out_weight == 0:
                sinks.append(source)
    for loop in holder.loops:
        for side in loop.occupied_sides:
            _set_slot(loop, side, loop_segments[loop].slot)
    next_free = [0] * len(holder.node.ports)
    for side in _SIDES[1:]:
        loops = sorted((loop for loop in holder.loops if side in loop.occupied_sides),
                       key=lambda loop: loop.routing_slot[_SIDES.index(side)])
        ids = [port.id for port in holder.node.ports if port.side == side]
        if not ids:
            for index, loop in enumerate(loops):
                _set_slot(loop, side, index)
        else:
            # Source allocates the empty label-slot array even though every
            # label branch is skipped under the no-label guard.
            slot_assigned_to_label = [0] * len(label_crossings)
            for loop in loops:
                available = 0
                for index in range(min(ids), max(ids) + 1):
                    if activities[loop][index]:
                        available = max(available, next_free[index])
                _set_slot(loop, side, available)
                for index in range(min(ids), max(ids) + 1):
                    if activities[loop][index]:
                        next_free[index] = available + 1
    # Source routing-slot-assignment fields are invocation-local here; no
    # segment/map/activity container survives this function or escapes.


def _route_orthogonal(holder):
    node = holder.node
    edge_spacing, node_spacing = 10.0, 10.0
    positions = [[0.0] * count for count in holder.routing_slot_count]
    baselines = {"NORTH": -node.margin.top - node_spacing,
                 "EAST": node.size.x + node.margin.right + node_spacing,
                 "SOUTH": node.size.y + node.margin.bottom + node_spacing,
                 "WEST": -node.margin.left - node_spacing}
    for side in _SIDES[1:]:
        current = baselines[side]
        factor = -1 if side in ("NORTH", "WEST") else 1
        for slot in range(len(positions[_SIDES.index(side)])):
            largest_label = positions[_SIDES.index(side)][slot]
            positions[_SIDES.index(side)][slot] = current
            current += factor * (largest_label + edge_spacing)
    top, right, bottom, left = node.margin.top, node.margin.right, node.margin.bottom, node.margin.left
    for loop in holder.loops:
        for wrapped in loop.edges:
            # NORTH/NORTH -> source $addCornerBendPoints early return;
            # OrthogonalSelfLoopRouter.modifyBendPoints returns the same chain.
            points = []
            for port_wrapper in (wrapped.source, wrapped.target):
                port = port_wrapper.port
                anchor_x = port.pos.x
                anchor_y = port.pos.y
                anchor_x += port.anchor.x
                anchor_y += port.anchor.y
                point = Vec2(0.0, positions[1][loop.routing_slot[1]])
                point.x += anchor_x
                points.append(point)
            wrapped.edge.bend_points.clear()
            wrapped.edge.bend_points.extend(points)
            for point in points:
                left = max(left, -point.x)
                right = max(right, point.x - node.size.x)
                top = max(top, -point.y)
                bottom = max(bottom, point.y - node.size.y)
    node.margin.top, node.margin.right, node.margin.bottom, node.margin.left = top, right, bottom, left


def self_loop_router(graph):
    """Canonical $process_50 default orthogonal loop-route/slot path."""
    holders = _holders(graph)
    for holder in holders:
        node = holder.node
        if (holder.are_ports_hidden or not all(_finite(v) for v in
                (node.margin.top, node.margin.right, node.margin.bottom, node.margin.left))):
            _outside("Loop routing requires restored ports and finite prepared margins")
        expected_sources, expected_targets = [], []
        for loop in holder.loops:
            wrapped = loop.edges[0]
            expected_sources.append(wrapped.source.port)
            expected_targets.append(wrapped.target.port)
            if (loop.self_loop_type != "ONE_SIDE" or loop.labels is not None
                    or wrapped.edge.source is not None or wrapped.edge.target is not None
                    or set(loop.ports_by_side) != {"NORTH"}
                    or len(loop.ports_by_side["NORTH"]) != 2
                    or set(loop.ports_by_side["NORTH"]) != set(loop.ports)
                    or any(p.port.owner is not node or p.port.side != "NORTH"
                           or p.port.incoming_edges or p.port.outgoing_edges
                           or not all(_finite(v) for v in (p.port.pos.x, p.port.pos.y, p.port.anchor.x, p.port.anchor.y))
                           for p in loop.ports)):
                _outside("Only independently restored empty-adjacency NORTH loops are reviewed")
        if [p for p in node.ports if p.side == "NORTH"] != expected_sources[::-1] + expected_targets:
            _outside("The source STACKED nested-port invariant is missing")
        if any(p.side not in ("NORTH", "EAST", "WEST") for p in node.ports):
            _outside("Other self-loop sides are outside the reviewed default route")
    for holder in holders:
        for index, port in enumerate(holder.node.ports):
            port.id = index
        for loop in holder.loops:
            loop.ports.sort(key=lambda wrapped: wrapped.port.id)
            side_ports = loop.ports_by_side.get("NORTH")
            loop.leftmost_port = min(side_ports, key=lambda wrapped: wrapped.port.id)
            loop.rightmost_port = max(side_ports, key=lambda wrapped: wrapped.port.id)
            if "NORTH" not in loop.occupied_sides:
                loop.occupied_sides.append("NORTH")
        _assign_slots(holder)
        _route_orthogonal(holder)


def snapshot_holder(holder, value):
    """Pure selected-field observer; does not materialize defaults or draw RNG."""
    def edge_view(edge):
        return {"reference": value(edge), "source": value(edge.source), "target": value(edge.target),
                "bendPoints": value(edge.bend_points), "properties": value(edge.properties)}

    def port_view(wrapped):
        port = wrapped.port
        return {"reference": value(port), "id": port.id, "owner": value(port.owner), "side": port.side,
                "pos": value(port.pos), "size": value(port.size), "anchor": value(port.anchor),
                "properties": value(port.properties), "incoming": [edge_view(e) for e in port.incoming_edges],
                "outgoing": [edge_view(e) for e in port.outgoing_edges],
                "isHidden": wrapped.is_hidden, "hadOnlySelfLoops": wrapped.had_only_self_loops}

    return {"node": value(holder.node), "arePortsHidden": holder.are_ports_hidden,
            "routingSlotCount": list(holder.routing_slot_count),
            "ports": [port_view(port) for port in holder.ports.values()],
            "loops": [{"portOrder": [value(p.port) for p in loop.ports],
                       "selfLoopType": loop.self_loop_type, "occupiedSides": list(loop.occupied_sides),
                       "portsBySide": {side: [value(p.port) for p in ports]
                                       for side, ports in loop.ports_by_side.items()},
                       "leftmostPort": None if loop.leftmost_port is None else value(loop.leftmost_port.port),
                       "rightmostPort": None if loop.rightmost_port is None else value(loop.rightmost_port.port),
                       "routingSlot": list(loop.routing_slot), "labelsPresent": loop.labels is not None,
                       "edges": [{"sourcePort": value(e.source.port), "targetPort": value(e.target.port),
                                  "edge": edge_view(e.edge)} for e in loop.edges]} for loop in holder.loops]}
