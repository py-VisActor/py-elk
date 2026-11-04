# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright (c) Kiel University and others.
# Sort helper: Copyright 2008 Google Inc. Apache-2.0; NOTICE-GWT-Ports.md.
# Fuzzy comparison uses original host arithmetic, not copied Guava code.
# Fixed elkjs0.12.1 worker275e6caf, common20324–20825/layered42125–43611.
"""Layered horizontal compaction with actual edge geometry and NS strategy."""
import math
from collections import deque

from ...execution.diagnostics import BasicProgressMonitor
from .compaction_graph import (CNode, OwnedCGroup, CGraph, Quadruplet, StrategyCompactor,
                               _ScanlineConstraints, _ActiveIntervals)
from .cell_layout import Rectangle, _maximum
from .port_label_placement import _minimum
from .graph import LNode, Vec2
from .wrapping import incoming, outgoing, read
from .property_access import read_layered_scalar
from .native_adapters import _read_property
from .orthogonal_general import get_junction_points
from .ports import _source_sort, double_compare
from .spacings import get_individual_or_default, _property
from ..disco import _IdentityMap
from ..radial import IdentitySet


def fuzzy_compare(a, b):
    if abs(a - b) <= 1e-4 or a == b or (math.isnan(a) and math.isnan(b)):
        return 0
    if a < b:
        return -1
    if a > b:
        return 1
    return int(math.isnan(a)) - int(math.isnan(b))


def _ceil(value):
    if value == 0 or not math.isfinite(value):
        return value
    result = float(math.ceil(value))
    return math.copysign(result, value) if result == 0 else result


def _int(value):
    # Source round_int is saturating truncation followed by JS |0.
    if math.isnan(value):
        return 0
    return int(max(-2147483648, min(2147483647, value)))


def _same_edge(first, second):
    a, b = first.origin, second.origin
    return (isinstance(a, VerticalSegment) and isinstance(b, VerticalSegment)
            and any(edge in b.represented_edges for edge in a.represented_edges))


class VerticalSegment:
    def __init__(self, first, second, parent, edge):
        self.potential_parents = [] if parent is None else [parent]
        self.represented_edges = [edge]
        self.affected_bends = [first, second]
        self.affected_boxes = []
        self.hitbox = Rectangle(_minimum(first.x, second.x), _minimum(first.y, second.y),
                                abs(first.x - second.x), abs(first.y - second.y))
        self.junction_points = []
        self.ignore_spacing = Quadruplet()
        self.constraints = []
        self.joined = []
        self.a_port = None
        junctions = get_junction_points(edge)
        if junctions is not None:
            for point in junctions:
                if fuzzy_compare(point.x, first.x) == 0:
                    self.junction_points.append(point)


class QuadraticConstraints:
    def calculate(self, compactor):
        for node in compactor.graph.nodes:
            node.constraints.clear()
        for first in compactor.graph.nodes:
            for second in compactor.graph.nodes:
                if first is second or (first.group is not None and first.group is second.group):
                    continue
                spacing = (compactor.spacings_handler.vertical(first, second)
                           if compactor.direction in ('LEFT', 'RIGHT')
                           else compactor.spacings_handler.horizontal(first, second))
                a, b = first.hitbox, second.hitbox
                if ((b.x > a.x or a.x == b.x and a.width < b.width)
                        and fuzzy_compare(b.y + b.height + spacing, a.y) > 0
                        and fuzzy_compare(b.y, a.y + a.height + spacing) < 0):
                    first.constraints.append(second)


class EdgeAwareScanlineConstraintCalculation:
    def __init__(self, graph):
        self.edge_spacing = read_layered_scalar(graph, 'SPACING_EDGE_EDGE', 'SPACING_EDGE_EDGE')
        self.routing = read_layered_scalar(graph, 'EDGE_ROUTING', 'EDGE_ROUTING')

    @staticmethod
    def _alter(node, spacing, factor):
        delta = spacing * factor
        if isinstance(node.origin, VerticalSegment):
            flags = node.origin.ignore_spacing
            if flags.up:
                if not flags.down:
                    node.hitbox.height += delta + .01
            else:
                node.hitbox.y -= delta + .01
                node.hitbox.height += delta + .01
        elif isinstance(node.origin, LNode):
            node.hitbox.y -= delta
            node.hitbox.height += 2 * delta

    def _alter_group(self, group, spacing, factor):
        master = getattr(group, 'master', None)
        if master is None:
            master = next(iter(group.nodes))
        self._alter(master, spacing, factor)
        if len(group.nodes) == 1:
            return
        delta = spacing * factor
        for node in group.nodes:
            if node is not master:
                flags = node.origin.ignore_spacing
                if flags.up:
                    node.hitbox.y += delta + .01
                    node.hitbox.height -= delta + .01
                elif flags.down:
                    node.hitbox.height -= delta + .01

    def _minimum_spacing(self, nodes):
        result = None
        for node in nodes:
            origin = node.origin
            if isinstance(origin, LNode) and origin.type == 'EXTERNAL_PORT':
                value = math.inf
            elif isinstance(origin, VerticalSegment):
                value = _maximum(0, self.edge_spacing / 2 - .5)
            elif isinstance(origin, LNode):
                value = _maximum(0, get_individual_or_default(origin, _property('SPACING_NODE_NODE_0')) / 2 - .5)
            else:
                value = math.inf
            result = value if result is None else _minimum(result, value)
        return 0 if result is None else result

    def _sweep(self, compactor, predicate):
        points = [(node, low) for node in compactor.graph.nodes if predicate(node) for low in (True, False)]
        for i, node in enumerate(compactor.graph.nodes):
            node.id = i
        intervals = _ActiveIntervals()
        candidates = [None] * len(compactor.graph.nodes)
        _source_sort(points, _ScanlineConstraints._compare)
        for node, low in points:
            if low:
                _, equal = intervals._locate(node)
                if equal:
                    raise RuntimeError('Invalid hitboxes for scanline constraint calculation.')
                intervals.add(node)
                candidates[node.id] = intervals.lower(node)
                right = intervals.higher(node)
                if right is not None:
                    candidates[right.id] = node
            else:
                left = intervals.lower(node)
                if left is not None and left is candidates[node.id] and left.group is not None and left.group is not node.group:
                    left.constraints.append(node)
                right = intervals.higher(node)
                if right is not None and candidates[right.id] is node and right.group is not None and right.group is not node.group:
                    node.constraints.append(right)
                intervals.remove(node)

    def calculate(self, compactor):
        nodes = compactor.graph.nodes
        if self.routing == 'ORTHOGONAL':
            segments = [node for node in nodes if isinstance(node.origin, VerticalSegment)]
            spacing = _maximum(0, self.edge_spacing / 2 - .5)
            for node in segments:
                self._alter(node, spacing, 1)
            self._sweep(compactor, lambda n: isinstance(n.origin, VerticalSegment))
            for node in segments:
                self._alter(node, spacing, -1)
            changed = []
            for node in nodes:
                if isinstance(node.origin, LNode):
                    space = _maximum(0, get_individual_or_default(node.origin, _property('SPACING_EDGE_EDGE')) / 2 - .5)
                    self._alter(node, space, 1)
                    changed.append((node, space))
            self._sweep(compactor, lambda n: isinstance(n.origin, LNode))
            for node, space in changed:
                self._alter(node, space, -1)
            spacing = self._minimum_spacing(nodes)
            for group in compactor.graph.groups:
                self._alter_group(group, spacing, 1)
            self._sweep(compactor, lambda n: True)
            for group in compactor.graph.groups:
                self._alter_group(group, spacing, -1)
        elif self.routing == 'SPLINES':
            self._sweep(compactor, lambda n: isinstance(n.origin, VerticalSegment))
            spacing = self._minimum_spacing(nodes)
            changed = [node for node in nodes if isinstance(node.origin, LNode)]
            for node in changed:
                self._alter(node, spacing, 1)
            self._sweep(compactor, lambda n: True)
            for node in changed:
                self._alter(node, spacing, -1)
        else:
            raise ValueError('Unsupported configuration')


class LGraphToCGraphTransformer:
    def __init__(self, graph):
        self.graph = graph
        self.nodes = _IdentityMap(graph)
        self.comments = _IdentityMap(graph)
        self.vertical = _IdentityMap(graph)
        self.locks = _IdentityMap(graph)
        self.routing = read_layered_scalar(graph, 'EDGE_ROUTING', 'EDGE_ROUTING')
        has_edges = False
        for i, layer in enumerate(graph.layers):
            layer.id = i
            for node in layer.nodes:
                if not has_edges and (next(incoming(node), None) is not None or next(outgoing(node), None) is not None):
                    has_edges = True
        directions = {'UNDEFINED', 'LEFT', 'RIGHT'}
        if not has_edges:
            directions.update(('UP', 'DOWN'))
        self.c_graph = CGraph(directions)
        self.c_graph.identity_owner = graph
        self.c_graph.predefined_horizontal_constraints = []
        self.c_graph.predefined_vertical_constraints = []

    def _new_cnode(self, origin, box):
        node = CNode(self.c_graph, box)
        node.origin = origin
        self.c_graph.nodes.append(node)
        return node

    def _transform_nodes(self):
        for layer in self.graph.layers:
            for node in layer.nodes:
                if read_layered_scalar(node, 'COMMENT_BOX', 'COMMENT_BOX'):
                    edge = next((e for p in node.ports for e in [*p.incoming_edges, *p.outgoing_edges]), None)
                    if edge is not None:
                        other = edge.source.owner
                        if other is node:
                            other = edge.target.owner
                        self.comments.put(node, (other, Vec2(node.pos.x - other.pos.x, node.pos.y - other.pos.y)))
                        continue
                margin = node.margin
                box = Rectangle(node.pos.x - margin.left, node.pos.y - margin.top,
                                node.size.x + margin.left + margin.right,
                                node.size.y + margin.top + margin.bottom)
                cnode = self._new_cnode(node, box)
                group = OwnedCGroup(self.graph, (cnode,))
                group.master = cnode
                self.c_graph.groups.append(group)
                difference = sum(1 for _ in incoming(node)) - sum(1 for _ in outgoing(node))
                lock = Quadruplet(left=difference < 0, right=difference > 0)
                if node.type == 'EXTERNAL_PORT':
                    lock.left = lock.right = lock.up = lock.down = True
                self.locks.put(cnode, lock)
                self.nodes.put(node, cnode)

    def _orthogonal_segments(self):
        segments = []
        for layer in self.graph.layers:
            for node in layer.nodes:
                cnode = self.nodes.get(node)
                for edge in outgoing(node):
                    bends = iter(edge.bend_points)
                    first_bend = next(bends, None)
                    if first_bend is None:
                        continue
                    first, last = True, None
                    box = cnode.hitbox
                    if edge.source.side in ('NORTH', 'SOUTH'):
                        y = box.y if edge.source.side == 'NORTH' else box.y + box.height
                        segment = VerticalSegment(first_bend, Vec2(first_bend.x, y), cnode, edge)
                        segment.ignore_spacing.down = edge.source.side == 'NORTH'
                        segment.ignore_spacing.up = edge.source.side == 'SOUTH'
                        segment.a_port = edge.source
                        segments.append(segment)
                    remaining = list(bends)
                    for i, second in enumerate(remaining):
                        if fuzzy_compare(first_bend.y, second.y) != 0:
                            last = VerticalSegment(first_bend, second, None, edge)
                            segments.append(last)
                            if first:
                                first = False
                                last.ignore_spacing.down = second.y < box.y or box.y <= second.y <= box.y + box.height
                                last.ignore_spacing.up = second.y > box.y + box.height or box.y <= second.y <= box.y + box.height
                        if i + 1 < len(remaining):
                            first_bend = second
                    if last is not None:
                        target = self.nodes.get(edge.target.owner).hitbox
                        if first_bend.y < target.y:
                            last.ignore_spacing.down = True
                        elif first_bend.y > target.y + target.height:
                            last.ignore_spacing.up = True
                        else:
                            last.ignore_spacing.up = last.ignore_spacing.down = True
                for edge in incoming(node):
                    if edge.bend_points and edge.target.side in ('NORTH', 'SOUTH'):
                        bend = edge.bend_points[-1]
                        y = cnode.hitbox.y if edge.target.side == 'NORTH' else cnode.hitbox.y + cnode.hitbox.height
                        segment = VerticalSegment(bend, Vec2(bend.x, y), cnode, edge)
                        segment.ignore_spacing.down = edge.target.side == 'NORTH'
                        segment.ignore_spacing.up = edge.target.side == 'SOUTH'
                        segment.a_port = edge.target
                        segments.append(segment)
        return segments

    def _spline_segments(self):
        segments = []
        for layer in self.graph.layers:
            for node in layer.nodes:
                for edge in outgoing(node):
                    chain = edge.properties.get('SPLINE_ROUTE_START')
                    if chain is None:
                        continue
                    last = None
                    for segment in chain:
                        if segment.is_straight:
                            continue
                        box = segment.bounding_box
                        edges = segment.edges.values()
                        vs = VerticalSegment(Vec2(box.x, box.y), Vec2(box.x + box.width, box.y + box.height), None, edges[0])
                        vs.affected_boxes.append(box)
                        segments.append(vs)
                        if last is not None:
                            last.constraints.append(vs)
                        last = vs
        return segments

    def _to_cnode(self, segment):
        box = segment.hitbox
        node = self._new_cnode(segment, Rectangle(box.x, box.y, box.width, box.height))
        node.spacing_ignore = segment.ignore_spacing
        if segment.potential_parents:
            segment.potential_parents[0].group.add_node(node)
        inc, out = IdentitySet(self.graph), IdentitySet(self.graph)
        for edge in segment.represented_edges:
            inc.add(edge.source)
            out.add(edge.target)
        difference = len(inc.values()) - len(out.values())
        self.locks.put(node, Quadruplet(left=difference < 0, right=difference > 0))
        for joined in segment.joined:
            self.vertical.put(joined, node)
        self.vertical.put(segment, node)

    def transform(self):
        self._transform_nodes()
        if self.routing == 'ORTHOGONAL':
            segments = self._orthogonal_segments()
        elif self.routing == 'SPLINES':
            segments = self._spline_segments()
        else:
            raise RuntimeError('Compaction not supported for ' + self.routing + ' edges.')
        def compare(first, second):
            result = fuzzy_compare(first.hitbox.x, second.hitbox.x)
            return result if result else double_compare(first.hitbox.y, second.hitbox.y)
        _source_sort(segments, compare)
        survivor = None
        for segment in segments:
            if survivor is None:
                survivor = segment
                continue
            a, b = survivor.hitbox, segment.hitbox
            if (fuzzy_compare(a.x, b.x) == 0 and not (fuzzy_compare(a.y + a.height, b.y) < 0 or fuzzy_compare(b.y + b.height, a.y) < 0)):
                for name in ('represented_edges', 'affected_bends', 'affected_boxes', 'junction_points', 'constraints', 'potential_parents'):
                    getattr(survivor, name).extend(getattr(segment, name))
                x, y = _minimum(a.x, b.x), _minimum(a.y, b.y)
                width = _maximum(a.x + a.width, b.x + b.width) - x
                height = _maximum(a.y + a.height, b.y + b.height) - y
                a.x, a.y, a.width, a.height = x, y, width, height
                for direction in ('left', 'right', 'up', 'down'):
                    setattr(survivor.ignore_spacing, direction, getattr(survivor.ignore_spacing, direction) | getattr(segment.ignore_spacing, direction))
                if survivor.a_port is None:
                    survivor.a_port = segment.a_port
                survivor.joined.extend(segment.joined)
                survivor.joined.append(segment)
            else:
                self._to_cnode(survivor)
                survivor = segment
        if survivor is not None:
            self._to_cnode(survivor)
        for segment, node in self.vertical.items():
            for other in segment.constraints:
                self.c_graph.predefined_horizontal_constraints.append((node, self.vertical.get(other)))
        return self.c_graph

    def _adjust_between(self, left, right, left_index, right_index, spline):
        first, last = left_index, right_index
        if left.initial_segment and left.is_straight:
            box = self.nodes.get(left.source_node).hitbox
            start = box.x + box.width
            first -= 1
        else:
            start = left.bounding_box.x + left.bounding_box.width
        if right.last_segment and right.is_straight:
            end = self.nodes.get(right.target_node).hitbox.x
            last += 1
        else:
            end = right.bounding_box.x
        chunk = (end - start) / max(2, last - first)
        position = start + chunk
        for i in range(first, last):
            box = spline[i].bounding_box
            box.x = position - box.width / 2
            position += chunk

    def _adjust_spline(self, spline):
        if not spline:
            return
        last = spline[0]
        if len(spline) == 1:
            self._adjust_between(last, last, 1, 0, spline)
            return
        i = 1
        while i < len(spline):
            if last.initial_segment or not last.is_straight:
                found = next(((j, spline[j]) for j in range(i, len(spline))
                              if j == len(spline) - 1 or not spline[j].is_straight), None)
                if found is not None:
                    j, following = found
                    self._adjust_between(last, following, i, j, spline)
                    i, last = j + 1, following

    def apply_layout(self):
        for node in self.c_graph.nodes:
            if isinstance(node.origin, LNode):
                node.origin.pos.x = node.hitbox.x + node.origin.margin.left
        for comment, (other, offset) in self.comments.items():
            comment.pos.x, comment.pos.y = other.pos.x + offset.x, other.pos.y + offset.y
        for node in self.c_graph.nodes:
            if isinstance(node.origin, VerticalSegment):
                segment = node.origin
                delta = node.hitbox.x - node.hitbox_pre_compaction.x
                for point in segment.affected_bends:
                    point.x += delta
                for box in segment.affected_boxes:
                    box.x += delta
                for point in segment.junction_points:
                    point.x += delta
        if self.routing == 'SPLINES':
            for original, cnode in self.nodes.items():
                for edge in outgoing(original):
                    if edge.source.owner is edge.target.owner:
                        delta = cnode.hitbox.x - cnode.hitbox_pre_compaction.x
                        for point in edge.bend_points:
                            point.x += delta
            for layer in self.graph.layers:
                for node in layer.nodes:
                    for edge in outgoing(node):
                        spline = edge.properties.get('SPLINE_ROUTE_START')
                        if spline is not None and spline:
                            self._adjust_spline(spline)
        for original, cnode in self.nodes.items():
            for edge in outgoing(original):
                if edge.source.owner is edge.target.owner:
                    delta = cnode.hitbox.x - cnode.hitbox_pre_compaction.x
                    for label in edge.labels:
                        label.pos.x += delta
        left = top = math.inf
        right = bottom = -math.inf
        for node in self.c_graph.nodes:
            box = node.hitbox
            left, top = _minimum(left, box.x), _minimum(top, box.y)
            right, bottom = _maximum(right, box.x + box.width), _maximum(bottom, box.y + box.height)
        self.graph.offset.x, self.graph.offset.y = -left, -top
        self.graph.size.x, self.graph.size.y = right - left, bottom - top
        for node in self.c_graph.nodes:
            original = node.origin
            if isinstance(original, LNode) and original.type == 'EXTERNAL_PORT':
                side = _read_property(original, 'EXT_PORT_SIDE')
                if side == 'WEST':
                    original.pos.x = left
                elif side == 'EAST':
                    original.pos.x = right - (original.size.x + original.margin.right)
                elif side == 'NORTH':
                    original.pos.y = top
                elif side == 'SOUTH':
                    original.pos.y = bottom - (original.size.y + original.margin.bottom)
        self.c_graph.groups.clear()
        self.c_graph.nodes.clear()


class SpecialSpacings:
    def __init__(self, graph):
        self.graph = graph

    def horizontal(self, first, second):
        if _same_edge(first, second):
            return 0
        a, b = first.origin, second.origin
        if ((isinstance(a, LNode) and a.type == 'EXTERNAL_PORT')
                or (isinstance(b, LNode) and b.type == 'EXTERNAL_PORT')):
            return 0
        return self.graph.properties['SPACINGS'].get_horizontal_spacing(a.type if isinstance(a, LNode) else 'LONG_EDGE', b.type if isinstance(b, LNode) else 'LONG_EDGE')

    def vertical(self, first, second):
        if _same_edge(first, second):
            return 1
        a, b = first.origin, second.origin
        return self.graph.properties['SPACINGS'].get_vertical_spacing(a.type if isinstance(a, LNode) else 'LONG_EDGE', b.type if isinstance(b, LNode) else 'LONG_EDGE')


class NetworkSimplexCompaction:
    def compact(self, compactor):
        from .layering import _NNode, _NEdge
        from .network_simplex_general import _refresh
        from .network_simplex_placement import _PlacementNetworkSimplex
        nodes, edges = [], []
        def new_node(origin=None):
            result = _NNode(origin, len(nodes))
            nodes.append(result)
            return result
        def new_edge(first, second, delta, weight):
            edge = _NEdge(first, second, len(edges), delta=_int(delta), weight=float(weight))
            first.outgoing.append(edge)
            second.incoming.append(edge)
            edges.append(edge)
        groups = []
        for i, group in enumerate(compactor.graph.groups):
            group.id = i
            groups.append(new_node(group))
        for node in compactor.graph.nodes:
            for other in node.constraints:
                if node.group is other.group:
                    continue
                spacing = compactor.spacings_handler.horizontal(node, other) if compactor.direction in ('LEFT', 'RIGHT') else compactor.spacings_handler.vertical(node, other)
                delta = _maximum(0, _ceil(node.group_offset.x + node.hitbox.width + spacing - other.group_offset.x))
                if _same_edge(node, other):
                    helper = new_node()
                    offset = _int(_ceil(other.group_offset.x - node.group_offset.x))
                    adjust = offset - (other.group_offset.x - node.group_offset.x)
                    port, alter = node.origin.a_port, node
                    if port is None:
                        port, alter, adjust = other.origin.a_port, other, -adjust
                    if port is not None:
                        alter.group_offset.x -= adjust
                        port.pos.x -= adjust
                    new_edge(helper, groups[node.group.id], max(0, offset), 1)
                    new_edge(helper, groups[other.group.id], max(0, -offset), 1)
                else:
                    weight = 2 if isinstance(node.origin, VerticalSegment) != isinstance(other.origin, VerticalSegment) else 1
                    new_edge(groups[node.group.id], groups[other.group.id], delta, weight)
        by_node, by_edge = {}, {}
        for node in compactor.graph.nodes:
            if isinstance(node.origin, LNode):
                by_node[node.origin] = node
            elif isinstance(node.origin, VerticalSegment):
                for edge in node.origin.represented_edges:
                    by_edge.setdefault(edge, []).append(node)
        for node in compactor.graph.nodes:
            if not isinstance(node.origin, LNode):
                continue
            for edge in outgoing(node.origin):
                if edge.source.owner is edge.target.owner:
                    continue
                source_port, target_port = edge.source, edge.target
                if source_port.side in ('NORTH', 'SOUTH') and target_port.side in ('NORTH', 'SOUTH'):
                    continue
                target = by_node[target_port.owner]
                new_edge(groups[node.group.id], groups[target.group.id], 0, 100)
                if source_port.side == 'WEST' and source_port.outgoing_edges:
                    for other in by_edge.get(edge, []):
                        if other.hitbox.x < node.hitbox.x and other.group is not node.group:
                            new_edge(groups[other.group.id], groups[node.group.id], 1, 100)
                if target_port.side == 'EAST' and target_port.incoming_edges:
                    for other in by_edge.get(edge, []):
                        if other.hitbox.x > node.hitbox.x and other.group is not node.group:
                            new_edge(groups[node.group.id], groups[other.group.id], 1, 100)
        sources = [node for node in nodes if not node.incoming]
        if len(sources) > 1:
            artificial = new_node()
            for node in sources:
                new_edge(artificial, node, 1, 0)
        for node in nodes:
            _refresh(node)
        _PlacementNetworkSimplex(nodes, edges).execute(2147483647)
        for node in compactor.graph.nodes:
            node.hitbox.x = groups[node.group.id].layer + node.group_offset.x


class HorizontalGraphCompactor:
    source_name = 'HorizontalGraphCompactor'

    def get_layout_processor_configuration(self, graph):
        return None

    def process(self, graph, monitor=None):
        strategy = read(graph, 'COMPACTION_POST_COMPACTION_STRATEGY')
        if strategy == 'NONE':
            return
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Horizontal Compaction', 1)
        transformer = LGraphToCGraphTransformer(graph)
        compactor = StrategyCompactor(transformer.transform())
        compactor.set_spacings_handler(SpecialSpacings(graph))
        constraints = read(graph, 'COMPACTION_POST_COMPACTION_CONSTRAINTS')
        compactor.set_constraint_algorithm(EdgeAwareScanlineConstraintCalculation(graph) if constraints == 'SCANLINE' else QuadraticConstraints())
        if strategy == 'LEFT':
            compactor.compact()
        elif strategy == 'RIGHT':
            compactor.change_direction('RIGHT').compact()
        elif strategy == 'LEFT_RIGHT_CONSTRAINT_LOCKING':
            compactor.compact().change_direction('RIGHT').set_locking_strategy(lambda pair: pair[0].group.out_degree_real == 0).compact()
        elif strategy == 'LEFT_RIGHT_CONNECTION_LOCKING':
            compactor.compact().change_direction('RIGHT').set_locking_strategy(lambda pair: transformer.locks.get(pair[0]).get(pair[1])).compact()
        elif strategy == 'EDGE_LENGTH':
            compactor.set_compaction_algorithm(NetworkSimplexCompaction()).compact()
        compactor.change_direction('LEFT')
        compactor.finished = True
        transformer.apply_layout()
        monitor.done()
