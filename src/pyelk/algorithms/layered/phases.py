# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# ELK-derived kernels retain EPL-2.0 OR GPL-3.0-or-later below.
# Apache-2.0 applies to the adapted JavaRandom/signed arithmetic helper portions.
# GWT Random attribution: Copyright 2009 Google Inc.; ASF contributors.
# Includes modifications by Richard Zschech as well as Google.
# Python adaptation uses a native 48-bit state, checks and draw-count diagnostics.
# See pyelk/_licenses/NOTICE-GWT-Random.md and Apache-2.0.txt.
# GWT 2.13.0 is comparison material, not a proven exact worker build input.
# Constrained mechanical port from elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source/branch maps: references/e04-source-components-B.json;
# E05 GREEDY/LayerSweep: references/e05-source-components-B.json;
# NETWORK_SIMPLEX: references/e05-source-components-A.json.
# BK: references/e05-source-components-B.json; routing: e05-source-routing.json.
# E06 cycle/NS delegates: e06-source-components-A.json; remaining phases:
# references/e06-source-components-R.json; NOTICE-E06.md.
# Exact external Java build is unresolved. See pyelk/_licenses/NOTICE.md.
"""Source-reviewed bounded kernels, never a general layered implementation.

The caller admits ADR0005 inputs and runs the real intervening processors.
These kernels also check their own structural and numeric preconditions.
Singleton-layer reductions preserve graph mutations and random consumption;
they do not dispatch on public IDs or read oracle/reference data.
E06 approves GREEDY/NETWORK_SIMPLEX for up to eight original NORMAL nodes,
and LayerSweep/BK/routing for the bounded proper work graph after real cycle
breaking, loop preprocessing and long-edge splitting. Public admission is a
separate obligation; these components do not choose a layout by input identity.
"""
from collections import deque
import math

from ..._errors import UnsupportedFeatureError

_MASK48 = (1 << 48) - 1
_MULTIPLIER = 0x5DEECE66D
_P = "org.eclipse.elk."


def _signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >= (1 << (bits - 1)) else value


class JavaRandom:
    """Seeded fixed generated java.util.Random, including its GWT arithmetic.

    This is the seeded constructor only; it does not implement the pipeline's
    seed-zero Date.now/uniqueSeed path. Diagnostics never determine geometry.
    """
    def __init__(self, seed):
        self._primitive_draws = 0
        self.set_seed(seed)

    @property
    def state48(self):
        return self._state

    @property
    def primitive_draws(self):
        return self._primitive_draws

    @property
    def seedhi(self):
        return self._state >> 24

    @property
    def seedlo(self):
        return self._state & 0xFFFFFF

    def set_seed(self, seed):
        if type(seed) is not int or not -(1 << 63) <= seed < (1 << 63):
            raise ValueError("A signed 64-bit seed is required")
        self._state = (seed ^ _MULTIPLIER) & _MASK48

    def next(self, bits):
        if type(bits) is not int or not 1 <= bits <= 32:
            raise ValueError("Primitive random width must be between 1 and 32")
        self._state = (self._state * _MULTIPLIER + 11) & _MASK48
        self._primitive_draws += 1
        value = self._state >> (48 - bits)
        return _signed(value, 32) if bits == 32 else value

    def next_int(self, bound):
        if type(bound) is not int or not 1 <= bound < (1 << 31):
            raise ValueError("A positive signed 32-bit bound is required")
        if (bound & -bound) == bound:
            return (bound * self.next(31)) >> 31
        while True:
            bits = self.next(31)
            value = bits % bound
            # Worker $nextInt uses JS number addition, with no int32 cast here.
            if bits - value + bound - 1 >= 0:
                return value

    def next_long(self):
        return _signed((self.next(32) << 32) + self.next(32), 64)

    def next_float(self):
        return self.next(24) * (2.0 ** -24)

    def next_double(self):
        return self.next(26) * (2.0 ** -26) + self.next(27) * (2.0 ** -53)


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PHASE_INPUT", "", message)


def _measure(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1_000_000
    except OverflowError:
        return False


def _zero(value):
    return type(value) in (int, float) and value == 0


def _path(graph, *, layered):
    """Validate adjacency independently of array order, return ordered path."""
    if layered:
        if graph.layerless_nodes or any(len(layer.nodes) != 1 for layer in graph.layers):
            _outside("This stage requires singleton layers and no layerless nodes")
        if any(layer.graph is not graph or layer.nodes[0].layer is not layer for layer in graph.layers):
            _outside("Layer/node membership is inconsistent")
        nodes = [layer.nodes[0] for layer in graph.layers]
    else:
        if graph.layers:
            _outside("This stage requires a layerless input")
        nodes = list(graph.layerless_nodes)
    if len(nodes) > 4 or len({id(node) for node in nodes}) != len(nodes):
        _outside("The reviewed phase slice has at most four distinct nodes")
    by_identity = {id(node): node for node in nodes}
    incoming, outgoing, edges = {node: [] for node in nodes}, {node: [] for node in nodes}, []
    seen_edges, seen_ports = set(), set()
    for node in nodes:
        if node.graph is not graph or node.type != "NORMAL" or not all(_measure(value) for value in (node.size.x, node.size.y)):
            _outside("Only normal nodes with bounded finite given dimensions are reviewed")
        if node.properties.get("LAYER_CONSTRAINT", "NONE") != "NONE" or node.properties.get("IN_LAYER_CONSTRAINT", "NONE") != "NONE":
            _outside("Non-default node constraints are outside this phase slice")
        for port in node.ports:
            if id(port) in seen_ports or port.owner is not node or port.origin is not None:
                _outside("Ports must be distinct implicit ports with correct owners")
            seen_ports.add(id(port))
            if any(len({id(edge) for edge in entries}) != len(entries) for entries in (port.incoming_edges, port.outgoing_edges)):
                _outside("Duplicate edge adjacency is outside the reviewed representation")
            for edge in port.outgoing_edges:
                if id(edge) in seen_edges or edge.source is not port or edge.target is None:
                    _outside("Outgoing adjacency is inconsistent")
                seen_edges.add(id(edge)); edges.append(edge)
                target = edge.target.owner
                if id(target) not in by_identity or edge not in edge.target.incoming_edges or edge.target not in target.ports:
                    _outside("Target adjacency is inconsistent")
                if target is node or edge.properties.get("REVERSED", False):
                    _outside("Self/reversed edges require a different source branch")
                if any(type(edge.properties.get(key, 0)) is not int or edge.properties.get(key, 0) != 0
                       for key in ("PRIORITY_DIRECTION", "PRIORITY_SHORTNESS", "PRIORITY_STRAIGHTNESS")):
                    _outside("Non-default priorities require a separate phase review")
                outgoing[node].append(edge); incoming[target].append(edge)
            for edge in port.incoming_edges:
                if edge.target is not port or edge.source is None or edge not in edge.source.outgoing_edges:
                    _outside("Incoming adjacency is inconsistent")
                if id(edge.source.owner) not in by_identity or edge.source not in edge.source.owner.ports:
                    _outside("Incoming source is outside the reviewed graph")
    if len(edges) != max(0, len(nodes) - 1) or any(len(incoming[node]) > 1 or len(outgoing[node]) > 1 for node in nodes):
        _outside("The reviewed topology is one directed path")
    if not nodes:
        return nodes, edges, incoming, outgoing
    starts = [node for node in nodes if not incoming[node]]
    if len(starts) != 1:
        _outside("A directed path needs one source")
    ordered, seen, current = [], set(), starts[0]
    while id(current) not in seen:
        ordered.append(current); seen.add(id(current))
        if not outgoing[current]:
            break
        current = outgoing[current][0].target.owner
    if len(ordered) != len(nodes) or (layered and ordered != nodes):
        _outside("All nodes must belong to the same forward layered path")
    return ordered, edges, incoming, outgoing


def _dag_before_layering(graph):
    """E05 GREEDY guard; validation never reorders or mutates the work graph."""
    if graph.layers:
        _outside("GREEDY requires the original layerless component")
    nodes = list(graph.layerless_nodes)
    if len(nodes) > 8 or len({id(node) for node in nodes}) != len(nodes):
        _outside("The reviewed acyclic GREEDY component has at most eight distinct nodes")
    by_identity = {id(node): node for node in nodes}
    incoming = {node: [] for node in nodes}
    outgoing = {node: [] for node in nodes}
    adjacent = {node: [] for node in nodes}
    edges, seen_edges, seen_ports, pairs = [], set(), set(), set()
    for node in nodes:
        if node.graph is not graph or node.type != "NORMAL" or not all(_measure(value) for value in (node.size.x, node.size.y)):
            _outside("Acyclic GREEDY requires original normal nodes with bounded finite dimensions")
        if node.properties.get("LAYER_CONSTRAINT", "NONE") != "NONE" or node.properties.get("IN_LAYER_CONSTRAINT", "NONE") != "NONE":
            _outside("Non-default node constraints are outside the acyclic GREEDY component")
        for port in node.ports:
            if id(port) in seen_ports or port.owner is not node or port.origin is not None:
                _outside("GREEDY ports must be distinct implicit ports with correct owners")
            seen_ports.add(id(port))
            if len(port.incoming_edges) + len(port.outgoing_edges) != 1:
                _outside("The reviewed importer creates one implicit port per edge endpoint")
            for edge in port.outgoing_edges:
                if id(edge) in seen_edges or edge.source is not port or edge.target is None:
                    _outside("GREEDY outgoing adjacency is inconsistent")
                seen_edges.add(id(edge))
                target = edge.target.owner
                if id(target) not in by_identity or edge.target not in target.ports or edge not in edge.target.incoming_edges:
                    _outside("GREEDY target adjacency is inconsistent")
                if target is node or (node, target) in pairs or edge.properties.get("REVERSED", False):
                    _outside("Self, parallel and reversed edges require a different GREEDY branch")
                if type(edge.properties.get("PRIORITY_DIRECTION", 0)) is not int or edge.properties.get("PRIORITY_DIRECTION", 0) != 0:
                    _outside("Only the default direction priority is approved for acyclic GREEDY")
                pairs.add((node, target))
                edges.append(edge)
                outgoing[node].append(edge)
                incoming[target].append(edge)
                adjacent[node].append(target)
                adjacent[target].append(node)
            for edge in port.incoming_edges:
                if edge.target is not port or edge.source is None or edge not in edge.source.outgoing_edges:
                    _outside("GREEDY incoming adjacency is inconsistent")
                if id(edge.source.owner) not in by_identity or edge.source not in edge.source.owner.ports:
                    _outside("GREEDY incoming source is outside the component")
    # This topological walk checks admission only. Actual IDs, queues and marks
    # below still follow the source component/port/edge order.
    degree = {node: len(incoming[node]) for node in nodes}
    ready = deque(node for node in nodes if degree[node] == 0)
    visited = 0
    while ready:
        node = ready.popleft()
        visited += 1
        for edge in outgoing[node]:
            degree[edge.target.owner] -= 1
            if degree[edge.target.owner] == 0:
                ready.append(edge.target.owner)
    if visited != len(nodes):
        _outside("The reviewed GREEDY branch requires an acyclic graph")
    connected = set()
    pending = nodes[:1]
    while pending:
        node = pending.pop()
        if node not in connected:
            connected.add(node)
            pending.extend(neighbor for neighbor in adjacent[node] if neighbor not in connected)
    if len(connected) != len(nodes):
        _outside("The reviewed GREEDY component must be connected")
    return nodes, edges, incoming, outgoing


def _implicit_sides(nodes, *, centered=False):
    for node in nodes:
        if node.properties.get("PORT_CONSTRAINTS") not in ("FIXED_SIDE", "FIXED_ORDER"):
            _outside("The real side/sort processors must run before this stage")
        if node.port_sides_cached is not True:
            _outside("The real port-side range cache must be prepared")
        sides = set()
        for port in node.ports:
            if port.side not in ("EAST", "WEST") or port.side in sides:
                _outside("A path has at most one implicit port on each flow side")
            sides.add(port.side)
            if not all(_zero(value) for value in (port.size.x, port.size.y, port.anchor.x, port.anchor.y)):
                _outside("Only zero-size zero-anchor implicit ports are reviewed")
            if ((port.side == "EAST" and (len(port.outgoing_edges) != 1 or port.incoming_edges))
                    or (port.side == "WEST" and (len(port.incoming_edges) != 1 or port.outgoing_edges))):
                _outside("Implicit path ports must have their expected edge direction")
            if centered and (not _measure(port.pos.x) or not _measure(port.pos.y)
                             or port.pos.y != node.size.y / 2 or port.pos.x != (node.size.x if port.side == "EAST" else 0)):
                _outside("The reviewed placement branch needs centered side ports")
        for side in sides:
            indexes = [index for index, port in enumerate(node.ports) if port.side == side]
            if node.port_side_indices.get(side) != (indexes[0], indexes[-1] + 1):
                _outside("Cached implicit-port side ranges are inconsistent")


def _rng(graph):
    if not isinstance(graph.random, JavaRandom):
        _outside("A verified generated JavaRandom stream is required")
    return graph.random


def greedy_cycle_breaker(graph):
    """Delegate the source-approved E06 real GREEDY component."""
    from .cycles import greedy_cycle_breaker as reviewed_breaker
    return reviewed_breaker(graph)


def network_simplex_layerer(graph, *, monitor=None):
    """Delegate the independently approved E05 NETWORK_SIMPLEX component."""
    from .layering import network_simplex_layerer as reviewed_layerer
    return reviewed_layerer(graph) if monitor is None else reviewed_layerer(graph, monitor=monitor)


def layer_sweep(graph, *, strategy):
    """Delegate the independently approved proper-DAG LayerSweep kernels."""
    from .crossing import layer_sweep as reviewed_sweep
    return reviewed_sweep(graph, strategy=strategy)


def bk_node_placer(graph, *, monitor=None):
    """Delegate the independently approved default proper-DAG BK component."""
    from .placement import bk_node_placer as reviewed_placer
    return reviewed_placer(graph) if monitor is None else reviewed_placer(graph, monitor=monitor)


def orthogonal_edge_router(graph):
    """Delegate the independently reviewed full default orthogonal router."""
    from .routing import orthogonal_edge_router as reviewed_router
    return reviewed_router(graph)
