# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# CC01-CC09 / HOST17/V/connected-component-compactor-source-review-01.
# Reuses attributed spore._fuzzy_compare at the source fixed1e-4 predicate.
"""Connected-component hull preparation and the actual compaction caller."""
from .cell_layout import Rectangle, _maximum
from .component_compaction import OneDimensionalComponentsCompaction, _DIRECTION_DOMAIN, _DIRECTION_ORDER
from .compaction_graph import _minimum
from .components_general import offset_graph
from .diagnostic_strings import _designation, node_text, port_designation
from .graph import LNode, LEdge, Vec2, set_source, set_target
from .graph_configurator import _graph_of
from .native_import_full import _new_port
from .native_adapters import _read_property
from .native_properties import CanonicalPropertyMap
from .property_access import read_layered_scalar
from .rectilinear_hull import Point, RectilinearConvexHull
from ..radial import IdentitySet
from ..spore import _fuzzy_compare
from ...execution.diagnostics import BasicProgressMonitor
from ...execution.enum_collections import EnumKeyMap
from ...execution.enum_identity import PORT_SIDE_ORDER


def _absolute_anchor(port):
    point = Vec2()
    for vector in (port.owner.pos, port.pos, port.anchor):
        point.x += vector.x
        point.y += vector.y
    return point


def _edge_text(edge):
    state = getattr(_graph_of(edge.source.owner), '_source_session', None)
    designation = _designation(edge, state)
    result = 'e_' + ('' if designation is None else designation)
    if edge.source is not None and edge.target is not None:
        result += (' ' + port_designation(edge.source, state) + '[' + node_text(edge.source.owner, state)
                   + '] -> ' + port_designation(edge.target, state) + '[' + node_text(edge.target.owner, state) + ']')
    return result


def _direction(side):
    return {'NORTH': 'UP', 'WEST': 'LEFT', 'EAST': 'RIGHT', 'SOUTH': 'DOWN'}.get(side, 'UNDEFINED')


class HullPoints(list):
    def __init__(self):
        super().__init__()
        self.top_left = Vec2(float('inf'), float('inf'))
        self.bottom_right = Vec2(-float('inf'), -float('inf'))

    def add(self, point):
        self.top_left.x = _minimum(self.top_left.x, point.x)
        self.top_left.y = _minimum(self.top_left.y, point.y)
        self.bottom_right.x = _maximum(self.bottom_right.x, point.x)
        self.bottom_right.y = _maximum(self.bottom_right.y, point.y)
        self.append(point)
        return True

    def add_vector(self, point):
        return self.add(Point(point.x, point.y))


class InternalComponent:
    def __init__(self, graph):
        self.external_extensions = []
        self.graph = graph
        self.contains_regular_nodes = False
        for node in graph.layerless_nodes:
            self.contains_regular_nodes = int(self.contains_regular_nodes) | int(node.type == 'NORMAL')

    def get_external_edges(self):
        edges = []
        for extension in self.external_extensions:
            edges.extend(extension.get_representative().values())
        return edges


class InternalConnectedComponents:
    def __init__(self):
        self.components = []


class InternalExternalExtension:
    def __init__(self, edge):
        self.edge = edge
        if edge.source.owner.type == 'EXTERNAL_PORT':
            self.external_port = edge.source
            self.external_port_side = _read_property(edge.source.owner, 'EXT_PORT_SIDE')
        elif edge.target.owner.type == 'EXTERNAL_PORT':
            self.external_port = edge.target
            self.external_port_side = _read_property(edge.target.owner, 'EXT_PORT_SIDE')
        else:
            raise ValueError('Edge ' + _edge_text(edge) + ' is not an external edge.')

    def get_placeholder(self):
        return None

    def get_representative(self):
        return self.edge

    def get_direction(self):
        return _direction(self.external_port_side)

    def get_representor(self):
        return getattr(self, 'external_extension', None)


class InternalUnionExternalExtension:
    def __init__(self, graph):
        self.edges = IdentitySet(graph)

    def get_representative(self):
        return self.edges

    def get_direction(self):
        return _direction(self.side)

    def get_placeholder(self):
        return self.placeholder

    def get_representor(self):
        return self.extension


class _ExternalEdges:
    def __init__(self, graph):
        self.graph = graph
        self.map = EnumKeyMap(_DIRECTION_DOMAIN, _DIRECTION_ORDER)

    def put(self, key, edge):
        values = self.map.get(key)
        if values is None:
            values = IdentitySet(self.graph)
            values.add(edge)
            self.map.put(key, values)
        else:
            values.add(edge)

    def values_for(self, key):
        values = self.map.get(key)
        return [] if values is None else values.values()


class _OuterSegments:
    def __init__(self):
        self.minimum = {side: float('inf') for side in PORT_SIDE_ORDER}
        self.maximum = {side: -float('inf') for side in PORT_SIDE_ORDER}
        self.extent = {side: -float('inf') for side in PORT_SIDE_ORDER}


def _element_bounds(points, element, offset):
    margin = element.margin
    points.add(Point(element.pos.x - margin.left + offset.x, element.pos.y - margin.top + offset.y))
    points.add(Point(element.pos.x - margin.left + offset.x, element.pos.y + element.size.y + margin.bottom + offset.y))
    points.add(Point(element.pos.x + element.size.x + margin.right + offset.x, element.pos.y - margin.top + offset.y))
    points.add(Point(element.pos.x + element.size.x + margin.right + offset.x, element.pos.y + element.size.y + margin.bottom + offset.y))


def component_hull_points(graph):
    points = HullPoints()
    for node in graph.layerless_nodes:
        if node.type == 'EXTERNAL_PORT':
            continue
        _element_bounds(points, node, Vec2())
        for port in node.ports:
            for edge in port.outgoing_edges:
                if edge.source.owner.type == 'EXTERNAL_PORT' or edge.target.owner.type == 'EXTERNAL_PORT':
                    continue
                for point in edge.bend_points:
                    points.add(Point(point.x, point.y))
    return points


def _create_dummy_node(graph):
    external = graph.layerless_nodes[0]
    node = LNode(graph, properties=CanonicalPropertyMap())
    node.labels = []
    graph.layerless_nodes.append(node)
    node.size.x = _maximum(1.0, external.size.x)
    node.size.y = _maximum(1.0, external.size.y)
    node.pos.x, node.pos.y = external.pos.x, external.pos.y
    side = _read_property(external, 'EXT_PORT_SIDE')
    if side == 'WEST':
        node.pos.x += 2
    elif side == 'NORTH':
        node.pos.y += 2
    elif side == 'EAST':
        node.pos.x -= 2
    elif side == 'SOUTH':
        node.pos.y -= 2
    port = _new_port(node)
    edge = LEdge(properties=CanonicalPropertyMap())
    edge.labels = []
    external_port = external.ports[0]
    set_source(edge, external_port)
    set_target(edge, port)
    port.pos.x, port.pos.y = 0.0, 0.0
    port.pos.x += external_port.pos.x
    port.pos.y += external_port.pos.y
    port.anchor.x, port.anchor.y = 0.0, 0.0
    port.anchor.x += external_port.anchor.x
    port.anchor.y += external_port.anchor.y
    return node


def _port_on_margin(port):
    original = _absolute_anchor(port)
    point = Vec2(original.x, original.y)
    margin = port.owner.margin
    if port.side == 'NORTH':
        point.y -= margin.top
    elif port.side == 'EAST':
        point.x += margin.right
    elif port.side == 'SOUTH':
        point.y += margin.bottom
    elif port.side == 'WEST':
        point.x -= margin.left
    return point


def _segment_rectangle(first, second, extent):
    return Rectangle(_minimum(first.x, second.x) - extent / 2,
                     _minimum(first.y, second.y) - extent / 2,
                     abs(first.x - second.x) + extent, abs(first.y - second.y) + extent)


class ComponentsCompactor:
    def external_port_position(self, point, side):
        if side == 'NORTH':
            return Vec2(point.x, _minimum(self.graph_top_left.y, point.y))
        if side == 'EAST':
            return Vec2(_maximum(self.graph_bottom_right.x, point.x), point.y)
        if side == 'SOUTH':
            return Vec2(point.x, _maximum(self.graph_bottom_right.y, point.y))
        if side == 'WEST':
            return Vec2(_minimum(point.x, self.graph_top_left.x), point.y)
        return Vec2(point.x, point.y)

    def _edge_segments(self, edge, extension):
        external, side = extension.external_port, extension.external_port_side
        first, second = _absolute_anchor(edge.source), _absolute_anchor(edge.target)
        if external is edge.source:
            first = self.external_port_position(first, side)
            second = _port_on_margin(edge.target)
        else:
            first = _port_on_margin(edge.source)
            second = self.external_port_position(second, side)
        points = [first, *edge.bend_points, second]
        outer_first = edge.source is external
        inner, outer = [], None
        for index in range(len(points) - 1):
            segment = points[index], points[index + 1]
            if outer_first and index == 0 or not outer_first and index == len(points) - 2:
                outer = segment
            else:
                inner.append(segment)
        return inner, outer

    def _transform_edge(self, edge, points, outer):
        extension = InternalExternalExtension(edge)
        inner, outer_segment = self._edge_segments(edge, extension)
        thickness = _maximum(read_layered_scalar(edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0'), 1.0)
        for first, second in inner:
            rectangle = _segment_rectangle(first, second, thickness)
            # Fixed worker strict-mode line30688 assigns an undeclared
            # returnVal. Preserve its actual failure after rectangle math,
            # before the first hull-point write. No implicit global repair.
            raise ReferenceError('returnVal is not defined')
        side = extension.external_port_side
        rectangle = _segment_rectangle(*outer_segment, thickness)
        if side in ('WEST', 'EAST'):
            outer.minimum[side] = _minimum(outer.minimum[side], rectangle.y)
            outer.maximum[side] = _maximum(outer.maximum[side], rectangle.y + rectangle.height)
        else:
            outer.minimum[side] = _minimum(outer.minimum[side], rectangle.x)
            outer.maximum[side] = _maximum(outer.maximum[side], rectangle.x + rectangle.width)
        extent = -float('inf')
        margin = extension.external_port.owner.margin
        if side == 'WEST':
            extent = margin.right
        elif side == 'EAST':
            extent = margin.left
        elif side == 'NORTH':
            extent = margin.bottom
        elif side == 'SOUTH':
            extent = margin.top
        outer.extent[side] = _maximum(outer.extent[side], extent)
        return extension

    def transform_graph(self, graph):
        component = InternalComponent(graph)
        if not component.contains_regular_nodes:
            _create_dummy_node(graph)
        points = component_hull_points(graph)
        external_edges, outer = _ExternalEdges(graph), _OuterSegments()
        for node in graph.layerless_nodes:
            for port in node.ports:
                for edge in port.outgoing_edges:
                    if edge.source.owner.type == 'EXTERNAL_PORT' or edge.target.owner.type == 'EXTERNAL_PORT':
                        extension = self._transform_edge(edge, points, outer)
                        external_edges.put(_direction(extension.external_port_side), extension.edge)
        extensions = []
        connections = _read_property(component.graph, 'EXT_PORT_CONNECTIONS')
        for side in PORT_SIDE_ORDER:
            if side not in connections:
                continue
            minimum, maximum, extent = outer.minimum[side], outer.maximum[side], outer.extent[side]
            extension = placeholder = None
            if side == 'WEST':
                extension = Rectangle(self.graph_top_left.x, minimum, points.top_left.x - self.graph_top_left.x, maximum - minimum)
                placeholder = Rectangle(self.graph_top_left.x, minimum, extent, maximum - minimum)
                points.add_vector(Vec2(extension.x + extension.width, extension.y))
                points.add_vector(Vec2(extension.x + extension.width, extension.y + extension.height))
            elif side == 'EAST':
                extension = Rectangle(points.bottom_right.x, minimum, self.graph_bottom_right.x - points.bottom_right.x, maximum - minimum)
                placeholder = Rectangle(self.graph_bottom_right.x - extent, minimum, extent, maximum - minimum)
                points.add_vector(Vec2(extension.x, extension.y))
                points.add_vector(Vec2(extension.x, extension.y + extension.height))
            elif side == 'NORTH':
                extension = Rectangle(minimum, self.graph_top_left.y, maximum - minimum, points.top_left.y - self.graph_top_left.y)
                placeholder = Rectangle(minimum, self.graph_top_left.y, maximum - minimum, extent)
                points.add_vector(Vec2(extension.x, extension.y + extension.height))
                points.add_vector(Vec2(extension.x + extension.width, extension.y + extension.height))
            elif side == 'SOUTH':
                extension = Rectangle(minimum, points.bottom_right.y, maximum - minimum, self.graph_bottom_right.y - points.bottom_right.y)
                placeholder = Rectangle(minimum, self.graph_bottom_right.y - extent, maximum - minimum, extent)
                points.add_vector(Vec2(extension.x, extension.y))
                points.add_vector(Vec2(extension.x + extension.width, extension.y))
            if extension is not None:
                union = InternalUnionExternalExtension(graph)
                union.side, union.extension, union.placeholder = side, extension, placeholder
                union.edges = IdentitySet(graph, external_edges.values_for(_direction(side)))
                extensions.append(union)
        component.external_extensions.extend(extensions)
        component.rectilinear_convex_hull = RectilinearConvexHull.of(points).split_into_rectangles()
        return component

    def compact(self, graphs, spacing):
        self.graph_top_left = Vec2(float('inf'), float('inf'))
        self.graph_bottom_right = Vec2(-float('inf'), -float('inf'))
        for graph in graphs:
            for node in graph.layerless_nodes:
                self.graph_top_left.x = _minimum(self.graph_top_left.x, node.pos.x - node.margin.left)
                self.graph_top_left.y = _minimum(self.graph_top_left.y, node.pos.y - node.margin.top)
                self.graph_bottom_right.x = _maximum(self.graph_bottom_right.x, node.pos.x + node.size.x + node.margin.right)
                self.graph_bottom_right.y = _maximum(self.graph_bottom_right.y, node.pos.y + node.size.y + node.margin.bottom)
        connected = InternalConnectedComponents()
        for graph in graphs:
            component = self.transform_graph(graph)
            connected.components.append(component)
            component.contains_regular_nodes = int(component.contains_regular_nodes) | int(bool(_read_property(component.graph, 'EXT_PORT_CONNECTIONS')))
        self.compactor = OneDimensionalComponentsCompaction(connected, spacing)
        BasicProgressMonitor()
        self.compactor.compact()
        self.yet_another_offset = Vec2()
        self.compacted_graph_size = self.compactor.transformer.graph_size
        for component in connected.components:
            offset = self.compactor.get_offset(component)
            offset_graph(component.graph, offset.x, offset.y)
            for node in component.graph.layerless_nodes:
                if node.type == 'EXTERNAL_PORT':
                    position = self.external_port_position(node.pos, _read_property(node, 'EXT_PORT_SIDE'))
                    node.pos.x, node.pos.y = 0.0, 0.0
                    node.pos.x += position.x
                    node.pos.y += position.y
        for component in connected.components:
            for edge in component.get_external_edges():
                points = [_absolute_anchor(edge.source), *edge.bend_points, _absolute_anchor(edge.target)]
                last = None
                for point in points:
                    if last is None:
                        last = point
                        continue
                    if _fuzzy_compare(last.x, point.x, 1.0e-4) == 0:
                        self.yet_another_offset.x = _minimum(self.yet_another_offset.x, last.x)
                        self.compacted_graph_size.x = _maximum(self.compacted_graph_size.x, last.x)
                    elif _fuzzy_compare(last.y, point.y, 1.0e-4) == 0:
                        self.yet_another_offset.y = _minimum(self.yet_another_offset.y, last.y)
                        self.compacted_graph_size.y = _maximum(self.compacted_graph_size.y, last.y)
                    last = point
        self.yet_another_offset.x = -self.yet_another_offset.x
        self.yet_another_offset.y = -self.yet_another_offset.y
        self.compacted_graph_size.x += self.yet_another_offset.x
        self.compacted_graph_size.y += self.yet_another_offset.y


def compact_components(components, target, spacing, *, include_offsets=False):
    """Actual three placer call sites: Source30302/30417/31218."""
    if include_offsets:
        for graph in components:
            offset_graph(graph, graph.offset.x, graph.offset.y)
    compactor = ComponentsCompactor()
    compactor.compact(components, spacing)
    for graph in components:
        graph.offset.x, graph.offset.y = 0.0, 0.0
        graph.offset.x += compactor.yet_another_offset.x
        graph.offset.y += compactor.yet_another_offset.y
    target.size.x, target.size.y = 0.0, 0.0
    target.size.x += compactor.compacted_graph_size.x
    target.size.y += compactor.compacted_graph_size.y
