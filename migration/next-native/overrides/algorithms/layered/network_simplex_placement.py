# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs0.12.1 worker275e6caf, 55994-56921 and common network-simplex core.
"""Auxiliary-graph Network Simplex placement, flexibility and path straightening."""
import math
from collections.abc import Mapping
from types import SimpleNamespace
from dataclasses import dataclass
from collections import deque
from ...execution.diagnostics import BasicProgressMonitor
from ...execution.identity import identity_hash
from ..disco import _IdentityMap
from ..radial import IdentitySet
from .graph import Insets, LNode
from .graph_info import get_graph_properties
from .layering import _NNode, _NEdge
from .network_simplex_general import _GeneralNetworkSimplex, _refresh
from .crossing_counter import _side_view
from .native_adapters import _read_property
from .ports import _source_sort, double_compare
from .port_distribution import _maximum, _minimum
from .property_access import read_layered_scalar
from .spacings import _property, get_individual_or_default

_CONFIGURATION = None
_FLEXIBLE_SIZE = ('NODE_SIZE_WHERE_SPACE_PERMITS', 'NODE_SIZE')


def _configuration():
    global _CONFIGURATION
    if _CONFIGURATION is None:
        from .layout_configuration import LayoutProcessorConfiguration, LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as I
        _CONFIGURATION = LayoutProcessorConfiguration()
        _CONFIGURATION.add_before(tuple(LayeredPhase)[4], I.HIERARCHICAL_PORT_POSITION_PROCESSOR)
    return _CONFIGURATION


def _graph(node): return node.graph if node.graph is not None else node.layer.graph


def _individual_surrounding(node):
    result = None
    if 'SPACING_INDIVIDUAL' in node.properties:
        individual = _read_property(node, 'SPACING_INDIVIDUAL')
        if not isinstance(individual, Mapping):
            raise TypeError('An actual individual spacing PropertyHolder is required')
        key = 'org.eclipse.elk.spacing.portsSurrounding'
        if key in individual:
            result = _read_property(SimpleNamespace(properties=individual), key)
    if result is None: result = _read_property(_graph(node), 'SPACING_PORTS_SURROUNDING')
    return result


def get_node_flexibility(node):
    key = 'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY'
    if key in node.properties:
        return read_layered_scalar(node, key, key + '_0')
    return read_layered_scalar(_graph(node), key + '_DEFAULT', key + '_DEFAULT_0')


def is_flexible_node(node):
    if node.type != 'NORMAL' or len(node.ports) <= 1: return False
    if read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0') == 'FIXED_POS': return False
    flexibility = get_node_flexibility(node)
    if flexibility == 'NONE': return False
    if flexibility not in _FLEXIBLE_SIZE:
        spacing = get_individual_or_default(node, _property('SPACING_PORT_PORT'))
        surrounding = _read_property(node, 'SPACING_PORTS_SURROUNDING')
        if surrounding is None: surrounding = Insets(spacing, spacing, spacing, spacing)
        west = _side_view(node, 'WEST')
        required = (surrounding.top + surrounding.bottom) + (len(west) - 1) * spacing
        if required > node.size.y: return False
        east = _side_view(node, 'EAST')
        required = (surrounding.top + surrounding.bottom) + (len(east) - 1) * spacing
        if required > node.size.y: return False
    return True


def is_handled_edge(edge):
    return edge.source.owner is not edge.target.owner and edge.source.owner.layer is not edge.target.owner.layer


def _connected(node):
    lists = [edges for p in node.ports for edges in (p.incoming_edges, p.outgoing_edges)]
    for edges in lists: yield from edges


def get_node_state(node):
    incoming = outgoing = 0
    for port in node.ports:
        incoming = ((incoming + sum(e.source.owner is not e.target.owner for e in port.incoming_edges) + 2**31) % 2**32) - 2**31
        outgoing = ((outgoing + sum(e.source.owner is not e.target.owner for e in port.outgoing_edges) + 2**31) % 2**32) - 2**31
        if incoming > 1 or outgoing > 1: return 2
    return 2 if incoming + outgoing == 1 else 0


def _ceil(value):
    if not math.isfinite(value) or value == 0: return value
    result = float(math.ceil(value))
    return math.copysign(result, value) if result == 0 else result


def _floor(value): return value if not math.isfinite(value) else float(math.floor(value))


def _round_long(value):
    if math.isnan(value): return 0
    if value >= 9223372036854775807: return 9223372036854775807
    if value <= -9223372036854775808: return -9223372036854775808
    base = math.floor(value)
    return base if value - base < .5 else base + 1


def _cast(value):
    if math.isnan(value): return 0
    return math.trunc(max(-2147483648, min(2147483647, value)))


@dataclass(eq=False)
class NodeRep:
    origin: object
    is_flexible: bool
    head: object
    tail: object


@dataclass(eq=False)
class EdgeRep:
    left: object
    right: object


class _PlacementNetworkSimplex(_GeneralNetworkSimplex):
    def execute(self, iteration_limit, *, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Network simplex', 1)
        if not self.nodes:
            monitor.done(); return
        for node in self.nodes: node.layer = 0
        prune = len(self.nodes) >= 40
        if prune: self._remove_subtrees()
        self._initialize(); self.feasible_tree()
        leave = self.leave_edge(); iterations = 0
        while leave is not None and iterations < iteration_limit:
            self.exchange(leave, self.enter_edge(leave))
            leave = self.leave_edge(); iterations += 1
        if prune: self._reattach_subtrees()
        # The placement caller explicitly requests withBalancing(false).
        self.normalize()
        self.cut = self.edges = self.tree_edges = self.edge_visited = None
        self.low = self.po = self.subtree_nodes_stack = None
        monitor.done()


class NetworkSimplexPlacer:
    source_name = 'NetworkSimplexPlacer'

    def __init__(self):
        _configuration()
        self.l_graph = None; self.n_nodes = None; self.n_edges = None
        self.node_reps = None; self.edge_reps = None; self.node_state = None
        self.crossing = None; self.two_paths = None; self.spacings = None
        self.node_count = self.edge_count = 0
        self.port_map = _IdentityMap(self)
        self.flexible_where_space_permits_edges = IdentitySet(self)

    def identity_hash(self, value):
        if value is None: return 0
        method = getattr(self.l_graph, 'identity_hash', None)
        return method(value) if method is not None else identity_hash(self.l_graph, value)

    def get_layout_processor_configuration(self, graph):
        return _configuration() if 'EXTERNAL_PORTS' in get_graph_properties(graph) else None

    def new_node(self, origin=None):
        node = _NNode(origin, len(self.n_nodes)); self.n_nodes.append(node); return node

    def new_edge(self, source, target, delta=0, weight=1):
        edge = _NEdge(source, target, len(self.n_edges), delta=int(delta), weight=float(weight))
        source.outgoing.append(edge); target.incoming.append(edge); self.n_edges.append(edge)
        return edge

    def prepare(self):
        self.n_nodes = []; self.n_edges = []; node_count = edge_count = 0
        for layer in self.l_graph.layers:
            for node in layer.nodes:
                node.id = node_count; node_count += 1
                for port in node.ports:
                    for edge in port.outgoing_edges:
                        edge.id = edge_count; edge_count += 1
                integer_anchor = is_flexible_node(node)
                for port in node.ports:
                    if integer_anchor:
                        y = port.anchor.y
                        if y != _floor(y): port.anchor.y -= y - float(_round_long(y))
                    y = port.pos.y + port.anchor.y
                    if y != _floor(y): port.pos.y -= y - float(_round_long(y))
        self.node_count = node_count; self.edge_count = edge_count
        self.node_reps = [None] * node_count; self.edge_reps = [None] * edge_count
        self.flexible_where_space_permits_edges.buckets.clear()

    def transform_ports(self, ports, corners):
        if not ports: return
        spacing = get_individual_or_default(corners.origin, _property('SPACING_PORT_PORT'))
        surrounding = _individual_surrounding(corners.origin)
        if surrounding is None: surrounding = Insets()
        last_node = corners.head; last_port = None
        for port in ports:
            gap = surrounding.top if last_port is None else spacing + last_port.size.y
            n = self.new_node(port); self.port_map.put(port, n)
            self.new_edge(last_node, n, _cast(_ceil(gap)), 0)
            last_port, last_node = port, n
        self.new_edge(last_node, corners.tail, _cast(_ceil(surrounding.bottom + last_port.size.y)), 0)

    def transform_layer(self, layer):
        previous = None
        for node in layer.nodes:
            if is_flexible_node(node):
                head = self.new_node(node); tail = self.new_node(node)
                rep = NodeRep(node, True, head, tail)
                flexibility = get_node_flexibility(node)
                size_edge = self.new_edge(head, tail, _cast(_ceil(node.size.y)), 1 if flexibility == 'NODE_SIZE' else 10000)
                if flexibility == 'NODE_SIZE_WHERE_SPACE_PERMITS':
                    self.flexible_where_space_permits_edges.add(size_edge)
                self.transform_ports(list(reversed(_side_view(node, 'WEST'))), rep)
                self.transform_ports(_side_view(node, 'EAST'), rep)
            else:
                n = self.new_node(node)
                for port in node.ports:
                    if port.side in ('EAST', 'WEST'): self.port_map.put(port, n)
                rep = NodeRep(node, False, n, n)
            self.node_reps[node.id] = rep
            if previous is not None:
                gap = (previous.origin.margin.bottom + self.spacings.get_vertical_spacing_nodes(previous.origin, node)) + node.margin.top
                if not previous.is_flexible: gap += previous.origin.size.y
                self.new_edge(previous.tail, rep.head, _cast(_ceil(gap)), 0)
            previous = rep

    @staticmethod
    def edge_weight(first, second):
        return 4 if first == second == 'NORMAL' else 8 if 'NORMAL' in (first, second) else 32

    def transform_edge(self, edge):
        dummy = self.new_node()
        source = self.node_reps[edge.source.owner.id]; target = self.node_reps[edge.target.owner.id]
        source_offset = edge.source.anchor.y; target_offset = edge.target.anchor.y
        if not source.is_flexible: source_offset += edge.source.pos.y
        if not target.is_flexible: target_offset += edge.target.pos.y
        target_delta = _cast(_maximum(0.0, source_offset - target_offset))
        source_delta = _cast(_maximum(0.0, target_offset - source_offset))
        priority = _maximum(1, read_layered_scalar(edge, 'PRIORITY_STRAIGHTNESS', 'PRIORITY_STRAIGHTNESS_0'))
        weight = priority * self.edge_weight(edge.source.owner.type, edge.target.owner.type)
        left = self.new_edge(dummy, self.port_map.get(edge.source), source_delta, weight)
        right = self.new_edge(dummy, self.port_map.get(edge.target), target_delta, weight)
        self.edge_reps[edge.id] = EdgeRep(left, right)

    def build_initial_auxiliary_graph(self):
        for layer in self.l_graph.layers: self.transform_layer(layer)
        for layer in self.l_graph.layers:
            for node in layer.nodes:
                for port in node.ports:
                    for edge in port.outgoing_edges:
                        if is_handled_edge(edge): self.transform_edge(edge)

    def add_north_south_edges(self, node):
        for port in _side_view(node, 'SOUTH'):
            other = port.properties.get('PORT_DUMMY')
            if other is not None:
                self.new_edge(self.node_reps[node.id].tail, self.node_reps[other.id].head, 0, .1)
        for port in _side_view(node, 'NORTH'):
            other = port.properties.get('PORT_DUMMY')
            if other is not None:
                self.new_edge(self.node_reps[other.id].tail, self.node_reps[node.id].head, 0, .1)

    def add_in_layer_edge(self, edge):
        source_dummy = edge.source.owner.type != 'NORMAL'
        port = edge.target if source_dummy else edge.source
        dummy = (edge.target if edge.source is port else edge.source).owner
        port_rep = self.port_map.get(port); dummy_rep = self.node_reps[dummy.id].head
        index = next((i for i, n in enumerate(port.owner.layer.nodes) if n is port.owner), -1) if port.owner.layer else -1
        dummy_index = next((i for i, n in enumerate(dummy.layer.nodes) if n is dummy), -1) if dummy.layer else -1
        self.new_edge(port_rep if index < dummy_index else dummy_rep,
                      dummy_rep if index < dummy_index else port_rep, 0, 4)

    def make_connected(self):
        for node in self.n_nodes: _refresh(node)
        visited = set(); representatives = []
        for first in self.n_nodes:
            if first in visited: continue
            representatives.append(first); visited.add(first)
            frames = [iter(first.connected)]
            while frames:
                try: edge = next(frames[-1])
                except StopIteration: frames.pop(); continue
                for other in (edge.source, edge.target):
                    if other not in visited:
                        visited.add(other); frames.append(iter(other.connected)); break
        if len(representatives) > 1:
            root = self.new_node()
            for node in representatives: self.new_edge(root, node, 0, 0)

    def solve(self, limit, monitor):
        for node in self.n_nodes: _refresh(node)
        _PlacementNetworkSimplex(self.n_nodes, self.n_edges).execute(limit, monitor=monitor)

    def mark_crossing_edges(self, left, right):
        opened = []
        for node in left.nodes:
            for port in _side_view(node, 'EAST'):
                for edge in port.outgoing_edges:
                    if is_handled_edge(edge) and edge.target.owner.layer is right: opened.append(edge)
        for node in reversed(right.nodes):
            for port in _side_view(node, 'WEST'):
                for edge in port.incoming_edges:
                    if not is_handled_edge(edge) or edge.source.owner.layer is not left: continue
                    if opened:
                        index = len(opened) - 1; last = opened[index]
                        while last is not edge and index > 0:
                            self.crossing[last.id] = self.crossing[edge.id] = True
                            index -= 1; last = opened[index]
                        if index > 0: opened.pop(index)

    def follow(self, edge, current, path):
        while True:
            other = edge.target.owner if edge.source.owner is current else edge.source.owner
            path.append(edge)
            if self.node_state[other.id] in (-1, 2) or self.crossing[edge.id]: return path
            self.node_state[other.id] = -1
            following = next((e for e in _connected(other) if is_handled_edge(e) and e is not edge), None)
            if following is None: return path
            edge, current = following, other

    def prefer_straight_edges(self):
        self.node_state = [0] * self.node_count; self.two_paths = []
        for layer in self.l_graph.layers:
            for node in layer.nodes: self.node_state[node.id] = get_node_state(node)
        self.crossing = [False] * self.edge_count
        for index in range(1, len(self.l_graph.layers)):
            self.mark_crossing_edges(self.l_graph.layers[index - 1], self.l_graph.layers[index])
        paths = []
        for layer in self.l_graph.layers:
            for node in layer.nodes:
                if self.node_state[node.id] != 2: continue
                for edge in _connected(node):
                    if not is_handled_edge(edge): continue
                    path = self.follow(edge, node, [])
                    if len(path) > 1: paths.append(path)
        for path in paths:
            if len(path) == 2:
                if path[0].target.owner is not path[1].source.owner: path[:] = [path[1], path[0]]
                if not is_flexible_node(path[0].target.owner): self.two_paths.append(path)
                continue
            if path[0].source.owner.type == 'LONG_EDGE' or any(e.target.owner.type == 'LONG_EDGE' for e in path): continue
            if get_node_flexibility(path[0].source.owner) in _FLEXIBLE_SIZE: continue
            if any(get_node_flexibility(e.target.owner) in _FLEXIBLE_SIZE for e in path): continue
            for index, edge in enumerate(path):
                weight = self.edge_weight('NORMAL', 'LONG_EDGE') if index == 0 or index == len(path) - 1 else self.edge_weight('LONG_EDGE', 'LONG_EDGE')
                weight *= 2
                rep = self.edge_reps[edge.id]
                old = rep.left.weight; rep.left.weight = _maximum(old, old + (weight - old))
                old = rep.right.weight; rep.right.weight = _maximum(old, old + (weight - old))

    @staticmethod
    def length(edge): return abs(edge.source.layer - edge.target.layer) - edge.delta

    def improve_two_path(self, path, probe):
        left = self.edge_reps[path[0].id]; right = self.edge_reps[path[1].id]
        left_delta = (left.left.target.layer - left.left.delta) - (left.right.target.layer - left.right.delta)
        right_delta = (right.left.target.layer - right.left.delta) - (right.right.target.layer - right.right.delta)
        if left_delta == 0 and right_delta == 0: return False
        center = left.right.target.origin
        if not isinstance(center, LNode): return False
        rep = self.node_reps[center.id]
        index = next((i for i, n in enumerate(center.layer.nodes) if n is center), -1) if center.layer else -1
        above_distance = below_distance = math.inf
        if index > 0:
            above = center.layer.nodes[index - 1]; above_rep = self.node_reps[above.id]
            spacing = _ceil(self.spacings.get_vertical_spacing_nodes(above, center))
            above_distance = (rep.head.layer - center.margin.top) - ((above_rep.head.layer + above.size.y) + above.margin.bottom) - spacing
        if index < len(center.layer.nodes) - 1:
            below = center.layer.nodes[index + 1]; below_rep = self.node_reps[below.id]
            spacing = _ceil(self.spacings.get_vertical_spacing_nodes(below, center))
            below_distance = (below_rep.head.layer - below.margin.top) - ((rep.head.layer + center.size.y) + center.margin.bottom) - spacing
        if probe and (abs(above_distance - below_distance) <= 1e-5 or above_distance == below_distance
                      or math.isnan(above_distance) and math.isnan(below_distance)): return True
        a = self.length(left.left); b = -self.length(left.right)
        c = -self.length(right.left); d = self.length(right.right)
        case_d = left_delta > 0 and right_delta < 0
        case_c = left_delta < 0 and right_delta > 0
        case_b = left.left.target.layer + left.right.delta < right.right.target.layer + right.left.delta
        case_a = left.left.target.layer + left.right.delta > right.right.target.layer + right.left.delta
        move = 0
        if not case_d and not case_c:
            if case_a:
                if above_distance + c > 0: move = c
                elif below_distance - a > 0: move = a
            elif case_b:
                if above_distance + b > 0: move = b
                elif below_distance - d > 0: move = d
        rep.head.layer += move
        if rep.is_flexible: rep.tail.layer += move
        return False

    def post_process_two_paths(self):
        queue = deque(self.two_paths); stack = []
        while queue:
            path = queue.popleft()
            if self.improve_two_path(path, True): stack.append(path)
        while stack: self.improve_two_path(stack.pop(), False)

    def apply_positions(self):
        for layer in self.l_graph.layers:
            for node in layer.nodes:
                rep = self.node_reps[node.id]; minimum = rep.head.layer; maximum = rep.tail.layer
                node.pos.y = float(minimum)
                delta = (maximum - minimum) - node.size.y
                flexible = is_flexible_node(node); flexibility = get_node_flexibility(node)
                if flexible and flexibility in _FLEXIBLE_SIZE: node.size.y += delta
                if flexible and flexibility in ('PORT_POSITION', *_FLEXIBLE_SIZE):
                    for port in node.ports:
                        if port.side in ('EAST', 'WEST'): port.pos.y = float(self.port_map.get(port).layer - minimum)
                    for label in node.labels:
                        placement = _read_property(node, 'NODE_LABELS_PLACEMENT')
                        if 'V_BOTTOM' in placement: label.pos.y += delta
                        elif 'V_CENTER' in placement: label.pos.y += delta / 2
                    if flexibility in _FLEXIBLE_SIZE:
                        for port in _side_view(node, 'SOUTH'): port.pos.y += delta

    def process(self, graph, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Network simplex node placement', 1)
        self.l_graph = graph; self.spacings = graph.properties.get('SPACINGS')
        self.prepare(); self.build_initial_auxiliary_graph()
        for layer in graph.layers:
            for node in layer.nodes: self.add_north_south_edges(node)
        for layer in graph.layers:
            for node in layer.nodes:
                if node.type != 'NORMAL': continue
                for edge in _connected(node):
                    if edge.source.owner is not edge.target.owner and edge.source.owner.layer is edge.target.owner.layer:
                        self.add_in_layer_edge(edge)
        favor = read_layered_scalar(graph, 'NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES', 'NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES_0')
        if type(favor) is not bool: raise TypeError('Actual favorStraightEdges Boolean required')
        if favor:
            pm = monitor.sub_task(1); pm.begin('Straight Edges Pre-Processing', 1)
            self.prefer_straight_edges(); pm.done()
        self.make_connected()
        limit = read_layered_scalar(graph, 'THOROUGHNESS', 'THOROUGHNESS_0') * len(self.n_nodes)
        self.solve(limit, monitor.sub_task(1))
        if self.flexible_where_space_permits_edges.values():
            pm = monitor.sub_task(1); pm.begin('Flexible Where Space Processing', 1)
            minimum = min(n.layer for n in self.n_nodes); maximum = max(n.layer for n in self.n_nodes)
            used = maximum - minimum; source = self.new_node(); sink = self.new_node()
            self.new_edge(source, sink, used, 20000)
            for rep in self.node_reps:
                if rep.origin.type == 'NORMAL' and len(rep.origin.ports) > 1:
                    self.new_edge(source, rep.tail, rep.tail.layer - minimum, 0)
                    self.new_edge(rep.head, sink, used - rep.head.layer, 0)
            for edge in self.flexible_where_space_permits_edges.values(): edge.weight = 1.0
            self.solve(limit, pm.sub_task(1)); pm.done()
        favor = read_layered_scalar(graph, 'NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES', 'NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES_0')
        if type(favor) is not bool: raise TypeError('Actual favorStraightEdges Boolean required')
        if favor:
            pm = monitor.sub_task(1); pm.begin('Straight Edges Post-Processing', 1)
            self.post_process_two_paths(); pm.done()
        self.apply_positions()
        self.l_graph = self.n_nodes = self.n_edges = self.node_reps = self.edge_reps = None
        self.port_map.keys.buckets.clear(); self.port_map.values_by_id.clear()
        self.node_state = self.crossing = self.two_paths = None
        self.flexible_where_space_permits_edges.buckets.clear()
        monitor.done()
