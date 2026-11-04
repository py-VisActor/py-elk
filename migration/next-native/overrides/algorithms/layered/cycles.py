# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Mechanical port from elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Components/proofs: references/e06-source-components-A.json
# Exact external Java build is unresolved. See pyelk/_licenses/NOTICE-E06.md.
"""Actual GREEDY cycle removal and restoration, with ordered identities.

These kernels do not expand public admission. The caller supplies the approved
native graph and runs the real intervening loop/long-edge/NS processors.
"""
from collections import deque
import math

from ..._errors import UnsupportedFeatureError
from .graph import LEdge, LGraph, LNode, LPort, Vec2, set_port_owner, set_source, set_target


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PHASE_INPUT", "", message)


def _boolean(properties, key):
    value = properties.get(key, False)
    if type(value) is not bool:
        _outside("Cycle properties require actual booleans")
    return value


def _dimension(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def _attached(edge):
    if not isinstance(edge, LEdge):
        raise TypeError("Expected an LEdge")
    source, target = edge.source, edge.target
    if not isinstance(source, LPort) or not isinstance(target, LPort):
        _outside("Cycle reversal requires two attached ports")
    if not isinstance(source.owner, LNode) or not isinstance(target.owner, LNode):
        _outside("Cycle reversal requires attached node ownership")
    if source.owner.graph is not target.owner.graph:
        _outside("Cycle reversal cannot cross work graphs")
    if source not in source.owner.ports or target not in target.owner.ports:
        _outside("Endpoint ports are absent from owner lists")
    if sum(item is edge for item in source.outgoing_edges) != 1 or sum(item is edge for item in target.incoming_edges) != 1:
        _outside("Cycle reversal requires exact bidirectional adjacency")
    if (edge.origin is not None and edge.origin.to_json().get("labels")
            and not hasattr(edge, "labels")):
        _outside("Edge labels require their actual native label views")
    if type(edge.bend_points) is not list or any(
        not isinstance(point, Vec2) or not all(type(v) in (int, float) and math.isfinite(v) for v in (point.x, point.y))
        for point in edge.bend_points
    ):
        _outside("Cycle reversal requires a finite vector chain")
    _boolean(edge.properties, "REVERSED")
    return source, target


def _provide_collector_port(node, *, output):
    """Actual provideCollectorPort first-match flag and attach/center writes."""
    from .ports import set_side
    flag = "OUTPUT_COLLECT" if output else "INPUT_COLLECT"
    for port in node.ports:
        if _boolean(port.properties, flag):
            return port
    port = LPort(properties={flag: True})
    set_port_owner(port, node)
    set_side(port, "EAST" if output else "WEST")
    port.pos.x, port.pos.y = (node.size.x if output else 0), node.size.y / 2
    return port


def reverse_edge(edge, *, adapt_ports):
    """E13-P05C actual collector adaptation, label reversal and bend copy.

    The replacement bend chain and its points are fresh objects. Source port
    geometry, original model direction and JUNCTION_POINTS stay untouched.
    """
    if type(adapt_ports) is not bool:
        raise TypeError("adapt_ports must be a boolean")
    old_source, old_target = _attached(edge)
    set_source(edge, None)
    set_target(edge, None)
    new_source = (_provide_collector_port(old_target.owner, output=True)
                  if adapt_ports and _boolean(old_target.properties, "INPUT_COLLECT") else old_target)
    set_source(edge, new_source)
    new_target = (_provide_collector_port(old_source.owner, output=False)
                  if adapt_ports and _boolean(old_source.properties, "OUTPUT_COLLECT") else old_source)
    set_target(edge, new_target)
    for label in getattr(edge, "labels", ()):
        placement = label.properties.get("EDGE_LABELS_PLACEMENT", "CENTER")
        if placement == "TAIL": label.properties["EDGE_LABELS_PLACEMENT"] = "HEAD"
        elif placement == "HEAD": label.properties["EDGE_LABELS_PLACEMENT"] = "TAIL"
    edge.properties["REVERSED"] = not _boolean(edge.properties, "REVERSED")
    edge.bend_points = [Vec2(point.x, point.y) for point in reversed(edge.bend_points)]


def _before_layering(graph):
    if not isinstance(graph, LGraph):
        raise TypeError("Expected an LGraph")
    if graph.layers:
        _outside("GREEDY requires the original layerless component")
    nodes = list(graph.layerless_nodes)
    if len(set(nodes)) != len(nodes):
        _outside("GREEDY requires distinct actual node identities")
    members = set(nodes)
    ports, edges = set(), set()
    for node in nodes:
        if node.graph is not graph or node.layer is not None:
            _outside("GREEDY requires actual layerless work nodes")
        if not all(_dimension(value) for value in (node.size.x, node.size.y)):
            _outside("GREEDY requires finite nonnegative native node dimensions")
        for port in node.ports:
            if port in ports or port.owner is not node:
                _outside("GREEDY requires distinct correctly owned ports")
            ports.add(port)
            for edge in port.incoming_edges:
                if edge.target is not port:
                    _outside("Incoming cycle adjacency differs from target")
                source, target = _attached(edge)
                if source.owner not in members or target.owner not in members:
                    _outside("Cycle endpoint is outside the current component")
            for edge in port.outgoing_edges:
                if edge.source is not port or edge in edges:
                    _outside("Outgoing cycle adjacency differs from source")
                source, target = _attached(edge)
                if source.owner not in members or target.owner not in members:
                    _outside("Cycle endpoint is outside the current component")
                if type(edge.properties.get("PRIORITY_DIRECTION", 0)) is not int:
                    _outside("Direction priority requires an actual native integer")
                edges.add(edge)
    from .phases import JavaRandom
    if not isinstance(graph.random, JavaRandom):
        _outside("The reviewed shared generated random stream is required")
    return nodes


def greedy_cycle_breaker(graph):
    """E13-P05C weighted $process_62/updateNeighbors over actual shared ports."""
    nodes = _before_layering(graph)
    indegree, outdegree, marks = [0.0] * len(nodes), [0.0] * len(nodes), [0] * len(nodes)
    sinks, sources = deque(), deque()
    for index, node in enumerate(nodes):
        node.id = index
        for port in node.ports:
            for edge in port.incoming_edges:
                if edge.source.owner is not node:
                    priority = edge.properties.get("PRIORITY_DIRECTION", 0)
                    indegree[index] += float(priority) + 1 if priority > 0 else 1
            for edge in port.outgoing_edges:
                if edge.target.owner is not node:
                    priority = edge.properties.get("PRIORITY_DIRECTION", 0)
                    outdegree[index] += float(priority) + 1 if priority > 0 else 1
        if outdegree[index] == 0:
            sinks.append(node)
        elif indegree[index] == 0:
            sources.append(node)

    def update_neighbors(node):
        for port in node.ports:
            for edge in [*port.incoming_edges, *port.outgoing_edges]:
                connected = edge.target if edge.source is port else edge.source
                neighbor = connected.owner
                if node is neighbor or marks[neighbor.id] != 0:
                    continue
                priority = max(0, edge.properties.get("PRIORITY_DIRECTION", 0))
                if edge.target is connected:
                    indegree[neighbor.id] -= float(priority) + 1
                    if indegree[neighbor.id] <= 0 and outdegree[neighbor.id] > 0:
                        sources.append(neighbor)
                else:
                    outdegree[neighbor.id] -= float(priority) + 1
                    if outdegree[neighbor.id] <= 0 and indegree[neighbor.id] > 0:
                        sinks.append(neighbor)

    remaining, next_right, next_left = len(nodes), -1, 1
    max_nodes = []
    while remaining > 0:
        while sinks:
            sink = sinks.popleft()
            marks[sink.id] = next_right
            next_right -= 1
            update_neighbors(sink)
            remaining -= 1
        while sources:
            source = sources.popleft()
            marks[source.id] = next_left
            next_left += 1
            update_neighbors(source)
            remaining -= 1
        if remaining > 0:
            max_outflow = -(1 << 31)
            for node in nodes:
                if marks[node.id] == 0:
                    outflow = outdegree[node.id] - indegree[node.id]
                    if outflow >= max_outflow:
                        if outflow > max_outflow:
                            max_nodes.clear()
                            max_outflow = outflow
                        max_nodes.append(node)
            # Even a unique maximum consumes the generated next(31) draw.
            max_node = max_nodes[graph.random.next_int(len(max_nodes))]
            marks[max_node.id] = next_left
            next_left += 1
            update_neighbors(max_node)
            remaining -= 1
    shift_base = len(nodes) + 1
    for index in range(len(nodes)):
        if marks[index] < 0:
            marks[index] += shift_base
    for node in nodes:
        for port in list(node.ports):
            for edge in list(port.outgoing_edges):
                if marks[node.id] > marks[edge.target.owner.id]:
                    reverse_edge(edge, adapt_ports=True)
                    graph.properties["CYCLIC"] = True
    # Scratch arrays/queues are local and disposed on return, as source null/reset.
    sources.clear()
    sinks.clear()


def restore_reversed_edges(graph):
    """Worker $process_46: per-port snapshot scan, with explicit false flags."""
    if not isinstance(graph, LGraph):
        raise TypeError("Expected an LGraph")
    for layer in graph.layers:
        for node in layer.nodes:
            for port in node.ports:
                for edge in list(port.outgoing_edges):
                    if _boolean(edge.properties, "REVERSED"):
                        reverse_edge(edge, adapt_ports=False)
