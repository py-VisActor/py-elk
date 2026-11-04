# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Constrained mechanical port from elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Component: references/e05-source-components-A.json, phase:NETWORK_SIMPLEX;
# E06 parallel/reversed provenance and scale: references/e06-source-components-A.json.
# E07 component driver/previous filling: references/e07-source-components-A.json.
# Exact external Java build is unresolved. See pyelk/_licenses/NOTICE.md.
"""Reviewed unit-weight network simplex, before long-edge insertion.

The private NNode/NEdge graph, ordered tight tree, cut values, exchanges and
balancing follow the fixed generated source. Validation is a host admission
check; it does not select ranks. This component computes no coordinates.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math

from ..._errors import UnsupportedFeatureError
from .graph import LGraph, Layer, LNode, set_layer

_MAX_INT = (1 << 31) - 1


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PHASE_INPUT", "", message)


def _admit(graph):
    if not isinstance(graph, LGraph) or graph.layers:
        _outside("Network simplex requires an original layerless graph")
    thoroughness = graph.properties.get("THOROUGHNESS", 7)
    if type(thoroughness) is not int or thoroughness != 7:
        _outside("Only the reviewed default network simplex thoroughness is supported")
    nodes = list(graph.layerless_nodes)
    if len(nodes) > 8 or len(set(nodes)) != len(nodes):
        _outside("The reviewed network simplex component has at most eight nodes")
    members = set(nodes)
    outgoing = {node: [] for node in nodes}
    incoming = {node: [] for node in nodes}
    seen_ports, seen_edges = set(), set()
    for node in nodes:
        if node.graph is not graph or node.layer is not None or node.type != "NORMAL":
            _outside("Only original unlayered NORMAL nodes are reviewed")
        if any(node.properties.get(key, "NONE") != "NONE"
               for key in ("LAYER_CONSTRAINT", "IN_LAYER_CONSTRAINT")):
            _outside("Only default node layer constraints are reviewed")
        for port in node.ports:
            if port in seen_ports or port.owner is not node or port.origin is not None:
                _outside("An implicit port must have one original owner")
            seen_ports.add(port)
            if len(port.incoming_edges) + len(port.outgoing_edges) != 1:
                _outside("One implicit port per edge endpoint is required")
            for edge in port.outgoing_edges:
                if edge in seen_edges or edge.source is not port or edge.target is None:
                    _outside("Outgoing adjacency is inconsistent")
                target = edge.target.owner
                if (target not in members or edge.target not in target.ports
                        or edge not in edge.target.incoming_edges):
                    _outside("Target adjacency is inconsistent")
                if type(edge.properties.get("REVERSED", False)) is not bool:
                    _outside("Edge reversal provenance must be a boolean")
                priority = edge.properties.get("PRIORITY_SHORTNESS", 0)
                if type(priority) is not int or priority != 0:
                    _outside("Only default shortness priority is reviewed")
                seen_edges.add(edge)
                # Source initialize_4 skips self-loops and creates a separate
                # private NEdge for every parallel nonself edge. REVERSED is
                # provenance; it is not read by the rank solver.
                if target is node:
                    continue
                outgoing[node].append(edge)
                incoming[target].append(edge)
            for edge in port.incoming_edges:
                if (edge.target is not port or edge.source is None
                        or edge.source.owner not in members
                        or edge.source not in edge.source.owner.ports
                        or edge not in edge.source.outgoing_edges):
                    _outside("Incoming adjacency is inconsistent")
    if len(seen_edges) > 28 or len(seen_ports) != 2 * len(seen_edges):
        _outside("At most 28 original edges with distinct implicit ports are reviewed")
    degree = {node: len(incoming[node]) for node in nodes}
    ready = deque(node for node in nodes if degree[node] == 0)
    visited = 0
    while ready:
        node = ready.popleft()
        visited += 1
        for edge in outgoing[node]:
            target = edge.target.owner
            degree[target] -= 1
            if degree[target] == 0:
                ready.append(target)
    if visited != len(nodes):
        _outside("Network simplex requires the reviewed acyclic input")
    if nodes:
        connected, pending = set(), [nodes[0]]
        while pending:
            node = pending.pop()
            if node not in connected:
                connected.add(node)
                pending.extend(edge.source.owner for edge in incoming[node])
                pending.extend(edge.target.owner for edge in outgoing[node])
        if (connected != members
                and graph.options.values.get("org.eclipse.elk.separateConnectedComponents") is not False):
            _outside("Disconnected work requires the actual separate=false caller branch")
    return nodes


@dataclass(eq=False)
class _NNode:
    origin: LNode
    id: int
    layer: int = 0
    incoming: list[_NEdge] = field(default_factory=list)
    outgoing: list[_NEdge] = field(default_factory=list)
    connected: list[_NEdge] = field(default_factory=list)
    unknown: list[_NEdge] = field(default_factory=list)
    tree: bool = False


@dataclass(eq=False)
class _NEdge:
    source: _NNode
    target: _NNode
    id: int = 0
    delta: int = 1
    weight: int = 1
    tree: bool = False

    def other(self, node):
        return self.target if self.source is node else self.source


def _connected_components(nodes):
    """Worker connectedComponents/DFS and its head-only size promotion."""
    for index, node in enumerate(nodes):
        node.id = index
    visited, components = set(), []

    def visit(node, ordered):
        visited.add(node)
        ordered.append(node)
        for port in node.ports:
            for edge in [*port.incoming_edges, *port.outgoing_edges]:
                opposite = edge.target if edge.source is port else edge.source
                if opposite.owner not in visited:
                    visit(opposite.owner, ordered)

    for node in nodes:
        if node not in visited:
            ordered = []
            visit(node, ordered)
            if not components or len(components[0]) < len(ordered):
                components.insert(0, ordered)
            else:
                components.append(ordered)
    return components


def _component_order(nodes):
    """Legacy private inspection helper; the actual driver keeps components."""
    return [node for component in _connected_components(nodes) for node in component]


def _private_graph(ordered):
    nodes = [_NNode(node, index) for index, node in enumerate(ordered)]
    by_origin = {node.origin: node for node in nodes}
    edges = []
    for node in nodes:
        for port in node.origin.ports:
            for original in port.outgoing_edges:
                if original.source.owner is original.target.owner:
                    continue
                edge = _NEdge(node, by_origin[original.target.owner], len(edges))
                node.outgoing.append(edge)
                edge.target.incoming.append(edge)
                edges.append(edge)
    # The private incoming list is appended in private edge creation order.
    # Its cached incident order is incoming then outgoing, not public edge order.
    for node in nodes:
        node.connected = [*node.incoming, *node.outgoing]
    return nodes, edges


class _NetworkSimplex:
    def __init__(self, nodes, edges, previous_layering_node_counts=None):
        self.nodes, self.edges = nodes, edges
        self.previous_layering_node_counts = previous_layering_node_counts
        self.tree_edges = []  # Source insertion-ordered identity set.
        self.edge_visited = [False] * len(edges)
        self.cut = [0] * len(edges)
        self.po = [0] * len(nodes)
        self.low = [0] * len(nodes)
        self.post_order = 1

    def topological_numbering(self):
        degree = [len(node.incoming) for node in self.nodes]
        sources = deque(node for node in self.nodes if not node.incoming)
        while sources:
            node = sources.popleft()
            for edge in node.outgoing:
                target = edge.target
                target.layer = max(target.layer, node.layer + edge.delta)
                degree[target.id] -= 1
                if degree[target.id] == 0:
                    sources.append(target)

    def tight_tree(self, node):
        count = 1
        node.tree = True
        for edge in node.connected:
            if not self.edge_visited[edge.id]:
                self.edge_visited[edge.id] = True
                other = edge.other(node)
                if edge.tree:
                    count += self.tight_tree(other)
                elif not other.tree and edge.delta == edge.target.layer - edge.source.layer:
                    edge.tree = True
                    self.tree_edges.append(edge)
                    count += self.tight_tree(other)
        return count

    def minimal_slack(self):
        minimum, selected = _MAX_INT, None
        for edge in self.edges:
            if edge.source.tree != edge.target.tree:
                slack = edge.target.layer - edge.source.layer - edge.delta
                if slack < minimum:
                    minimum, selected = slack, edge
        return selected

    def postorder(self, node):
        lowest = _MAX_INT
        for edge in node.connected:
            if edge.tree and not self.edge_visited[edge.id]:
                self.edge_visited[edge.id] = True
                lowest = min(lowest, self.postorder(edge.other(node)))
        self.po[node.id] = self.post_order
        self.low[node.id] = min(lowest, self.post_order)
        self.post_order += 1
        return self.low[node.id]

    def cutvalues(self):
        leaves = []
        for node in self.nodes:
            node.unknown = [edge for edge in node.connected if edge.tree]
            if len(node.unknown) == 1:
                leaves.append(node)
        for node in leaves:
            while len(node.unknown) == 1:
                determine = node.unknown[0]
                source, target = determine.source, determine.target
                self.cut[determine.id] = determine.weight
                for edge in node.connected:
                    if edge is determine:
                        continue
                    if edge.tree:
                        if source is edge.source or target is edge.target:
                            self.cut[determine.id] -= self.cut[edge.id] - edge.weight
                        else:
                            self.cut[determine.id] += self.cut[edge.id] - edge.weight
                    elif node is source:
                        self.cut[determine.id] += edge.weight if edge.source is node else -edge.weight
                    else:
                        self.cut[determine.id] += -edge.weight if edge.source is node else edge.weight
                source.unknown.remove(determine)
                target.unknown.remove(determine)
                node = target if source is node else source

    def feasible_tree(self):
        self.topological_numbering()
        if self.edges:
            while self.tight_tree(self.nodes[0]) < len(self.nodes):
                edge = self.minimal_slack()
                slack = edge.target.layer - edge.source.layer - edge.delta
                if edge.target.tree:
                    slack = -slack
                for node in self.nodes:
                    if node.tree:
                        node.layer += slack
                self.edge_visited = [False] * len(self.edges)
            self.edge_visited = [False] * len(self.edges)
            self.postorder(self.nodes[0])
            self.cutvalues()

    def in_head(self, node, edge):
        source, target = edge.source, edge.target
        inside_source = self.low[source.id] <= self.po[node.id] <= self.po[source.id]
        inside_target = self.low[target.id] <= self.po[node.id] <= self.po[target.id]
        # Preserve the generated source's literal interval expression.
        if inside_source and inside_target:
            if self.po[source.id] < self.po[target.id]:
                return False
            return True
        if self.po[source.id] < self.po[target.id]:
            return True
        return False

    def leave_edge(self):
        return next((edge for edge in self.tree_edges if self.cut[edge.id] < -1.0e-10), None)

    def enter_edge(self, leave):
        minimum, selected = _MAX_INT, None
        for edge in self.edges:
            if self.in_head(edge.source, leave) and not self.in_head(edge.target, leave):
                slack = edge.target.layer - edge.source.layer - edge.delta
                if slack < minimum:
                    minimum, selected = slack, edge
        return selected

    def exchange(self, leave, enter):
        leave.tree = False
        self.tree_edges.remove(leave)
        enter.tree = True
        self.tree_edges.append(enter)
        delta = enter.target.layer - enter.source.layer - enter.delta
        if not self.in_head(enter.target, leave):
            delta = -delta
        # in_head must continue using the OLD postorder intervals here.
        for node in self.nodes:
            if not self.in_head(node, leave):
                node.layer += delta
        self.post_order = 1
        self.edge_visited = [False] * len(self.edges)
        self.postorder(self.nodes[0])
        self.cutvalues()

    def normalize(self):
        lowest = min(node.layer for node in self.nodes)
        highest = max(node.layer for node in self.nodes)
        filling = [0] * (highest - lowest + 1)
        for node in self.nodes:
            node.layer -= lowest
            filling[node.layer] += 1
        if self.previous_layering_node_counts is not None:
            for index, count in enumerate(self.previous_layering_node_counts):
                filling[index] += count
                if index + 1 == len(filling):
                    break
        return filling

    @staticmethod
    def minimal_span(node):
        minimum_in = minimum_out = _MAX_INT
        for edge in node.connected:
            span = edge.target.layer - edge.source.layer
            # A non-minimal incoming edge can update minimum_out: this is the
            # fixed generated ternary, not an independently chosen formula.
            if edge.target is node and span < minimum_in:
                minimum_in = span
            elif span < minimum_out:
                minimum_out = span
        return (-1 if minimum_in == _MAX_INT else minimum_in,
                -1 if minimum_out == _MAX_INT else minimum_out)

    def balance(self, filling):
        for node in self.nodes:
            if len(node.incoming) == len(node.outgoing):
                new_layer = node.layer
                minimum_in, minimum_out = self.minimal_span(node)
                for index in range(node.layer - minimum_in + 1, node.layer + minimum_out):
                    if filling[index] < filling[new_layer]:
                        new_layer = index
                if filling[new_layer] < filling[node.layer]:
                    filling[node.layer] -= 1
                    filling[new_layer] += 1
                    node.layer = new_layer

    def execute(self, iteration_limit, *, monitor=None):
        if monitor is not None:
            monitor.begin('Network simplex', 1)
        if not self.nodes:
            if monitor is not None:
                monitor.done()
            return
        self.feasible_tree()
        leave = self.leave_edge()
        iterations = 0
        while leave is not None and iterations < iteration_limit:
            self.exchange(leave, self.enter_edge(leave))
            leave = self.leave_edge()
            iterations += 1
        self.balance(self.normalize())
        if monitor is not None:
            monitor.done()


def network_simplex_layerer(graph, *, monitor=None):
    """Worker NetworkSimplexLayerer + private NetworkSimplex, reviewed n<=8."""
    nodes = _admit(graph)
    if not nodes:
        return
    components = _connected_components(nodes)
    previous_counts = None
    for ordered in components:
        private_nodes, edges = _private_graph(ordered)
        # Fixed THOROUGHNESS=7, worker round_int(sqrt(n_i)), per component.
        iteration_limit = 28 * math.floor(math.sqrt(len(ordered)) + 0.5)
        solver = _NetworkSimplex(private_nodes, edges, previous_counts)
        if monitor is None:
            solver.execute(iteration_limit)
        else:
            solver.execute(iteration_limit, monitor=monitor.sub_task(1))
        for node in private_nodes:
            while len(graph.layers) <= node.layer:
                graph.layers.append(Layer(graph))
            set_layer(node.origin, graph.layers[node.layer])
        if len(components) > 1:
            previous_counts = [len(layer.nodes) for layer in graph.layers]
    graph.layerless_nodes.clear()
