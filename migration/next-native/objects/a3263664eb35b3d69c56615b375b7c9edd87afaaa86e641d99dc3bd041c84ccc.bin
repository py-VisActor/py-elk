# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Worker275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# P17B in references/e13-kernel-sources.json; actual Session holder views.
"""Source graph/node/port/label transforms for the new full Layered importer.

Outer graph/edge/hierarchy orchestration is added through separately approved
source blocks. These transforms never call the bounded public-slice resolver.
"""
from dataclasses import dataclass, field

from ...execution.node_micro import _Node, _Properties, _PropertyReader, VectorChain
from .graph import Insets, LEdge, LGraph, LNode, LPort, Vec2, set_port_owner, set_source, set_target
from .graph_configurator import get_direction
from .label_padding import compute_inside_node_label_padding
from .model_order_import import import_flat_model_order, transform_ordered_ports
from .native_properties import CanonicalPropertyMap, bind_native_properties
from .ports import calc_port_side, initialize_port, is_side_fixed, set_side
from .property_access import read_layered_scalar


@dataclass(eq=False)
class LLabel:
    text: str = ''
    pos: Vec2 = field(default_factory=Vec2)
    size: Vec2 = field(default_factory=Vec2)
    properties: object = field(default_factory=dict)
    id: int = 0


class _GenericGraphView:
    def __init__(self, reader, raw):
        self.properties = _Properties(reader, raw, 'node')
        self.options = None


class ElkGraphImporter:
    def __init__(self, state):
        self.state = state
        self.node_and_port_map = {}

    def _put(self, raw, native):
        # Source identity-key map requests share the Session's real allocator;
        # using id for lookup is not permission to omit hash-request effects.
        self.state.identity_hash(raw)
        self.node_and_port_map[id(raw)] = native

    def lookup(self, raw):
        if raw is None:
            return None
        self.state.identity_hash(raw)
        return self.node_and_port_map.get(id(raw))

    def _read(self, raw, symbol):
        return self.state.read_owner_scalar_property(raw, 'LayeredOptions', symbol)

    def _bind(self, raw, native):
        bind_native_properties(native, self.state.property_snapshot(raw))
        native.properties['ORIGIN'] = raw

    def _root(self, raw):
        current = raw
        while self.state.json_parents[id(current)] is not None:
            current = self.state.json_parents[id(current)]
        return current

    def _actual_label_manager(self, raw):
        # This actual Property id is deliberately NOT the catalogue's
        # org.eclipse.elk.labelManager. Unknown full ids remain exact.
        values = self.state.property_snapshot(raw).values
        return values.get('org.eclipse.elk.labels.labelManager')

    def create_lgraph(self, raw):
        graph = LGraph(origin=None, options=None, random=None)
        bind_native_properties(graph, self.state.property_snapshot(raw))
        graph._source_session = self.state
        graph.identity_hash = self.state.identity_hash
        if read_layered_scalar(graph, 'DIRECTION', 'DIRECTION') == 'UNDEFINED':
            graph.properties['DIRECTION'] = get_direction(graph)
        if graph.properties.get('org.eclipse.elk.labels.labelManager') is None:
            manager = self._actual_label_manager(self._root(raw))
            if manager is not None:
                # The fixed compiled fallback calls throwClassCastExceptionUnlessNull.
                raise TypeError('The fixed Layered label-manager fallback only accepts null')
            graph.properties['org.eclipse.elk.labels.labelManager'] = None
        graph.properties['ORIGIN'] = raw
        graph.properties['GRAPH_PROPERTIES'] = set()
        reader = _PropertyReader(self.state)
        parent = self.state.parents[id(raw)]
        parent_view = None if parent is None else _GenericGraphView(reader, parent)
        node_label_padding = compute_inside_node_label_padding(_Node(reader, raw, parent_view), 'RIGHT')
        padding = graph.properties.get('PADDING')
        if padding is None:
            padding = Insets(12.0, 12.0, 12.0, 12.0)
            graph.properties['PADDING'] = padding
        graph.padding.left += padding.left
        graph.padding.right += padding.right
        graph.padding.top += padding.top
        graph.padding.bottom += padding.bottom
        graph.padding.left += node_label_padding.left
        graph.padding.right += node_label_padding.right
        graph.padding.top += node_label_padding.top
        graph.padding.bottom += node_label_padding.bottom
        return graph

    def transform_label(self, raw):
        label = LLabel(raw.get('text', ''))
        self._bind(raw, label)
        label.size.x = raw.get('width', 0.0)
        label.size.y = raw.get('height', 0.0)
        label.pos.x = raw.get('x', 0.0)
        label.pos.y = raw.get('y', 0.0)
        return label

    def transform_node(self, raw, graph):
        node = LNode(graph)
        self._bind(raw, node)
        node.size.x = raw.get('width', 0.0)
        node.size.y = raw.get('height', 0.0)
        node.pos.x = raw.get('x', 0.0)
        node.pos.y = raw.get('y', 0.0)
        node.labels = []
        graph.layerless_nodes.append(node)
        self._put(raw, node)
        if raw.get('children') or self._read(raw, 'INSIDE_SELF_LOOPS_ACTIVATE'):
            node.properties['COMPOUND_NODE'] = True
        properties = graph.properties['GRAPH_PROPERTIES']
        constraints = read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
        if constraints == 'UNDEFINED':
            node.properties['PORT_CONSTRAINTS'] = 'FREE'
        elif constraints != 'FREE':
            properties.add('NON_FREE_PORTS')
        direction = read_layered_scalar(graph, 'DIRECTION', 'DIRECTION')
        transform_ordered_ports(self.state, raw,
                                lambda port: self.transform_port(port, node, properties, direction, constraints))
        for label in raw.get('labels', []):
            if not self._read(label, 'NO_LAYOUT') and label.get('text'):
                node.labels.append(self.transform_label(label))
        if read_layered_scalar(node, 'COMMENT_BOX', 'COMMENT_BOX'):
            properties.add('COMMENTS')
        if read_layered_scalar(node, 'HYPERNODE', 'HYPERNODE'):
            properties.add('HYPERNODES')
            properties.add('HYPEREDGES')
            node.properties['PORT_CONSTRAINTS'] = 'FREE'
        return node

    def _endpoint_node(self, identifier):
        shape = self.state.shapes[(type(identifier), identifier)]
        kind = self.state.kinds[id(shape)]
        if kind == 'node':
            return shape
        if kind == 'port':
            return self.state.owners[id(shape)]
        raise TypeError('A source connectable shape must be a node or port')

    def _is_self_loop(self, raw):
        common = None
        for identifiers in (raw.get('sources', []), raw.get('targets', [])):
            for identifier in identifiers:
                node = self._endpoint_node(identifier)
                if common is None:
                    common = node
                elif node is not common:
                    return False
        return True

    def _inside_connections(self, raw):
        owner = self.state.owners[id(raw)]
        for edge in self.state.incidence(raw):
            for identifier in edge.get('targets', []):
                if self.state._ancestor(self._endpoint_node(identifier), owner):
                    return True
        for edge in self.state.incidence(raw, True):
            for identifier in edge.get('sources', []):
                if self.state._ancestor(self._endpoint_node(identifier), owner):
                    return True
        for edge in self.state.incidence(raw):
            if self._is_self_loop(edge) and self._read(edge, 'INSIDE_SELF_LOOPS_YO'):
                return True
        return False

    def transform_port(self, raw, node, graph_properties, direction, original_constraints):
        port = LPort()
        bind_native_properties(port, self.state.property_snapshot(raw))
        set_side(port, self._read(raw, 'PORT_SIDE'))
        port.properties['ORIGIN'] = raw
        set_port_owner(port, node)
        port.size.x = raw.get('width', 0.0)
        port.size.y = raw.get('height', 0.0)
        port.pos.x = raw.get('x', 0.0)
        port.pos.y = raw.get('y', 0.0)
        port.labels = []
        self._put(raw, port)
        port.properties['INSIDE_CONNECTIONS'] = self._inside_connections(raw)
        initialize_port(port, original_constraints, direction, self._read(raw, 'PORT_ANCHOR'))
        for label in raw.get('labels', []):
            if not self._read(label, 'NO_LAYOUT') and label.get('text'):
                port.labels.append(self.transform_label(label))
        if direction in ('LEFT', 'RIGHT'):
            if port.side in ('NORTH', 'SOUTH'):
                graph_properties.add('NORTH_SOUTH_PORTS')
        elif direction in ('UP', 'DOWN'):
            if port.side in ('EAST', 'WEST'):
                graph_properties.add('NORTH_SOUTH_PORTS')
        return port

    def import_flat_graph(self, raw, graph):
        def transform_selected_edge(edge):
            source = self._simple_edge_node(edge)
            target = self._simple_edge_node(edge, True)
            enabled = self._read(source, 'INSIDE_SELF_LOOPS_ACTIVATE')
            laid_out = not self._read(edge, 'NO_LAYOUT')
            inside = enabled and self._is_self_loop(edge) and self._read(edge, 'INSIDE_SELF_LOOPS_YO')
            source_parent = self.state.parents[id(source)]
            siblings = source_parent is raw and source_parent is self.state.parents[id(target)]
            connects_graph = ((source_parent is raw and target is raw)
                              ^ (self.state.parents[id(target)] is raw and source is raw))
            if laid_out and not inside and (connects_graph or siblings):
                self.transform_edge(edge, raw, graph)
        import_flat_model_order(self.state, raw, graph,
                                transform_node=lambda node: self.transform_node(node, graph),
                                transform_edge=transform_selected_edge)
        parent = self.state.parents[id(raw)]
        if parent is not None:
            for edge in self.state.contained_edges(parent):
                source = self._simple_edge_node(edge)
                if source is raw and self._is_self_loop(edge):
                    inside = (self._read(source, 'INSIDE_SELF_LOOPS_ACTIVATE')
                              and self._read(edge, 'INSIDE_SELF_LOOPS_YO'))
                    if inside:
                        self.transform_edge(edge, raw, graph)

    def _simple_edge_node(self, raw, incoming=False):
        if len(raw.get('sources', [])) != 1 or len(raw.get('targets', [])) != 1:
            raise ValueError("Passed edge is not 'simple'.")
        return self._endpoint_node(raw['targets' if incoming else 'sources'][0])

    def _unsupported_graph(self, message):
        from ..._errors import UnsupportedFeatureError
        raise UnsupportedFeatureError('UNSUPPORTED_GRAPH', '', message)

    def check_edge_validity(self, raw):
        if not raw.get('sources'):
            self._unsupported_graph('Edges must have a source.')
        elif not raw.get('targets'):
            self._unsupported_graph('Edges must have a target.')
        elif len(raw['sources']) > 1 or len(raw['targets']) > 1:
            self._unsupported_graph('Hyperedges are not supported.')

    def _coordinate_frame(self, point, parent, *, absolute):
        while parent is not None:
            if absolute:
                point.x += parent.get('x', 0.0)
                point.y += parent.get('y', 0.0)
            else:
                point.x -= parent.get('x', 0.0)
                point.y -= parent.get('y', 0.0)
            parent = self.state.parents[id(parent)]

    def _section_endpoint(self, raw, section, name, parent):
        value = section[name]
        point = Vec2(value['x'], value['y'])
        self._coordinate_frame(point, self.state.current_containers[id(raw)], absolute=True)
        self._coordinate_frame(point, parent, absolute=False)
        return point

    def transform_edge(self, raw, parent, graph):
        self.check_edge_validity(raw)
        source_shape = self.state.endpoint(raw)
        target_shape = self.state.endpoint(raw, True)
        source_raw = self._endpoint_node(raw['sources'][0])
        target_raw = self._endpoint_node(raw['targets'][0])
        sections = raw.get('sections', [])
        section = sections[0] if sections else None
        source_node, target_node = self.lookup(source_raw), self.lookup(target_raw)
        source_port = target_port = None
        if self.state.kinds[id(source_shape)] == 'port':
            element = self.lookup(source_shape)
            if isinstance(element, LPort):
                source_port = element
            elif isinstance(element, LNode):
                source_node, source_port = element, element.ports[0]
        if self.state.kinds[id(target_shape)] == 'port':
            element = self.lookup(target_shape)
            if isinstance(element, LPort):
                target_port = element
            elif isinstance(element, LNode):
                target_node, target_port = element, element.ports[0]
        if source_node is None or target_node is None:
            from .raw_graph_strings import raw_edge_text
            self._unsupported_graph(
                'The source or the target of edge ' + raw_edge_text(self.state, raw)
                + ' could not be found. This usually happens when an edge connects a node laid out by ELK Layered to a node in '
                + 'another level of hierarchy laid out by either another instance of ELK Layered or another '
                + 'layout algorithm alltogether. The former can be solved by setting the hierarchyHandling '
                + 'option to INCLUDE_CHILDREN.')
        edge = LEdge()
        self._bind(raw, edge)
        edge.properties.pop('JUNCTION_POINTS', None)
        properties = graph.properties['GRAPH_PROPERTIES']
        if source_node is target_node:
            properties.add('SELF_LOOPS')
        if source_port is None:
            port_type, point = 'OUTPUT', None
            if section is not None and is_side_fixed(read_layered_scalar(source_node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')):
                point = self._section_endpoint(raw, section, 'startPoint', parent)
                if self.state._ancestor(target_raw, source_raw):
                    port_type = 'INPUT'
                    point.x += source_node.pos.x
                    point.y += source_node.pos.y
            source_port = self.create_port(source_node, point, port_type, graph)
        if target_port is None:
            port_type, point = 'INPUT', None
            if section is not None and is_side_fixed(read_layered_scalar(target_node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')):
                point = self._section_endpoint(raw, section, 'endPoint', parent)
            target_port = self.create_port(target_node, point, port_type, target_node.graph)
        set_source(edge, source_port)
        set_target(edge, target_port)
        if (len(source_port.incoming_edges) > 1 or len(source_port.outgoing_edges) > 1
                or len(target_port.incoming_edges) > 1 or len(target_port.outgoing_edges) > 1):
            properties.add('HYPEREDGES')
        edge.labels = []
        for label_raw in raw.get('labels', []):
            if not self._read(label_raw, 'NO_LAYOUT') and label_raw.get('text'):
                label = self.transform_label(label_raw)
                edge.labels.append(label)
                placement = read_layered_scalar(label, 'EDGE_LABELS_PLACEMENT', 'EDGE_LABELS_PLACEMENT')
                if placement in ('HEAD', 'TAIL'):
                    properties.add('END_LABELS')
                elif placement == 'CENTER':
                    properties.add('CENTER_LABELS')
                    label.properties['EDGE_LABELS_PLACEMENT'] = 'CENTER'
        crossing = read_layered_scalar(graph, 'CROSSING_MINIMIZATION_STRATEGY', 'CROSSING_MINIMIZATION_STRATEGY_0')
        placement = read_layered_scalar(graph, 'NODE_PLACEMENT_STRATEGY', 'NODE_PLACEMENT_STRATEGY_0')
        bends_required = crossing == 'INTERACTIVE' or placement == 'INTERACTIVE'
        if section is not None and section.get('bendPoints') and bends_required:
            points = [section['startPoint'], *section['bendPoints'], section['endPoint']]
            original = VectorChain(Vec2(point['x'], point['y']) for point in points)
            edge.properties['ORIGINAL_BENDPOINTS'] = VectorChain(Vec2(point.x, point.y) for point in original)
        return edge

    def provide_collector_port(self, node, port_type, side):
        key = 'OUTPUT_COLLECT' if port_type == 'OUTPUT' else 'INPUT_COLLECT'
        for port in node.ports:
            if port.properties.get(key, False):
                return port
        port = LPort()
        port.properties = CanonicalPropertyMap()
        port.integer_box_identities = port.properties.integer_boxes
        port.labels = []
        port.properties[key] = True
        set_port_owner(port, node)
        set_side(port, side)
        if side == 'NORTH':
            port.pos.x, port.pos.y = node.size.x / 2, 0.0
        elif side == 'EAST':
            port.pos.x, port.pos.y = node.size.x, node.size.y / 2
        elif side == 'SOUTH':
            port.pos.x, port.pos.y = node.size.x / 2, node.size.y
        elif side == 'WEST':
            port.pos.x, port.pos.y = 0.0, node.size.y / 2
        return port

    def create_port(self, node, endpoint, port_type, graph):
        direction = get_direction(graph)
        merge = read_layered_scalar(graph, 'MERGE_EDGES', 'MERGE_EDGES_0')
        hypernode = lambda: read_layered_scalar(node, 'HYPERNODE', 'HYPERNODE')
        default_side = {'RIGHT': 'EAST', 'LEFT': 'WEST', 'DOWN': 'SOUTH', 'UP': 'NORTH', 'UNDEFINED': 'UNDEFINED'}
        opposed = {'EAST': 'WEST', 'WEST': 'EAST', 'NORTH': 'SOUTH', 'SOUTH': 'NORTH', 'UNDEFINED': 'UNDEFINED'}
        if (merge or hypernode()) and not is_side_fixed(read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')):
            side = default_side[direction]
            return self.provide_collector_port(node, port_type, side if port_type == 'OUTPUT' else opposed[side])
        port = LPort()
        port.properties = CanonicalPropertyMap()
        port.integer_box_identities = port.properties.integer_boxes
        port.labels = []
        set_port_owner(port, node)
        if endpoint is not None:
            port.pos.x = endpoint.x - node.pos.x
            port.pos.y = endpoint.y - node.pos.y
            if node.size.x < 0 or node.size.y < 0:
                raise ValueError('The highx must be bigger then lowx and the highy must be bigger then lowy')
            if port.pos.x < 0:
                port.pos.x = 0.0
            elif port.pos.x > node.size.x:
                port.pos.x = node.size.x
            if port.pos.y < 0:
                port.pos.y = 0.0
            elif port.pos.y > node.size.y:
                port.pos.y = node.size.y
            set_side(port, calc_port_side(port, direction))
        else:
            side = default_side[direction]
            set_side(port, side if port_type == 'OUTPUT' else opposed[side])
        properties = graph.properties['GRAPH_PROPERTIES']
        if direction in ('RIGHT', 'LEFT'):
            if port.side in ('NORTH', 'SOUTH'):
                properties.add('NORTH_SOUTH_PORTS')
        elif direction in ('UP', 'DOWN') and port.side in ('WEST', 'EAST'):
            properties.add('NORTH_SOUTH_PORTS')
        return port
