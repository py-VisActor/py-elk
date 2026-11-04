# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P20 native transfer source closure.
"""Actual Layered layout transfer to the Session's owned working ELK graph."""
from ...execution.node_micro import _PropertyReader
from ..fixed import _port_side
from .cell_layout import _maximum
from .graph import Vec2
from .graph_configurator import _graph_of, get_node_flexibility
from .integer_box_tokens import value_of_integer_box
from .orthogonal_general import get_junction_points
from .ports import _divide
from .property_access import read_layered_scalar


_INCLUDE_LABEL = 'edgelabelcenterednessanalysis.includelabel'
_ZERO_OFFSET = Vec2()


def _sum_vectors(*vectors):
    result = Vec2()
    for vector in vectors:
        result.x += vector.x
        result.y += vector.y
    return result


def _descendant(child, parent):
    current = child
    following = getattr(_graph_of(current), 'parent_node', None)
    while following is not None:
        current = following
        if current is parent:
            return True
        following = getattr(_graph_of(current), 'parent_node', None)
    return False


class ElkGraphLayoutTransferrer:
    def __init__(self, state):
        self.state = state
        self.reader = _PropertyReader(state)

    def apply_layout(self, graph):
        pending = [graph]
        while pending:
            current = pending.pop()
            if not self._apply_one(current):
                continue
            # Continuation matches source recursive calls in layerless order.
            for node in reversed(current.layerless_nodes):
                nested = getattr(node, 'nested_graph', None)
                if nested is not None:
                    pending.append(nested)

    def _apply_one(self, graph):
        raw = graph.properties.get('ORIGIN')
        if self.state.kinds.get(id(raw)) != 'node':
            return False
        parent_node = getattr(graph, 'parent_node', None)
        offset = Vec2(graph.offset.x, graph.offset.y)
        offset.x += graph.padding.left
        offset.y += graph.padding.top
        if 'COMPUTE_PADDING' in self.reader.get(raw, 'node', 'nodeSize.options'):
            padding = self.reader.get(raw, 'node', 'padding')
            padding.bottom = graph.padding.bottom
            padding.top = graph.padding.top
            padding.left = graph.padding.left
            padding.right = graph.padding.right
        edges = []
        for node in graph.layerless_nodes:
            origin = node.properties.get('ORIGIN')
            kind = self.state.kinds.get(id(origin))
            if kind == 'node':
                self.apply_node_layout(node, offset)
            elif kind == 'port' and parent_node is None:
                position = self.external_port_position(graph, node, origin['width'], origin['height'])
                origin['x'], origin['y'] = position.x, position.y
            for port in node.ports:
                for edge in port.outgoing_edges:
                    if not _descendant(edge.target.owner, node):
                        edges.append(edge)
        if parent_node is not None:
            for port in parent_node.ports:
                for edge in port.outgoing_edges:
                    if _descendant(edge.target.owner, parent_node):
                        edges.append(edge)
        routing = self.state.read_owner_scalar_property(raw, 'LayeredOptions', 'EDGE_ROUTING')
        for edge in edges:
            self.apply_edge_layout(edge, routing, offset)
        self.apply_parent_node_layout(graph)
        return True

    def apply_node_layout(self, node, offset):
        raw = node.properties.get('ORIGIN')
        position_id = read_layered_scalar(node, 'CROSSING_MINIMIZATION_POSITION_ID', 'CROSSING_MINIMIZATION_POSITION_ID_0')
        layer_id = read_layered_scalar(node, 'LAYERING_LAYER_ID', 'LAYERING_LAYER_ID_0')
        for name, value in (('layered.crossingMinimization.positionId', position_id),
                            ('layered.layering.layerId', layer_id)):
            self.state.set_option(raw, name, value, integer_box=value_of_integer_box(value))
        raw['x'], raw['y'] = node.pos.x + offset.x, node.pos.y + offset.y
        if (self.reader.get(raw, 'node', 'nodeSize.constraints')
                or getattr(node, 'nested_graph', None) is not None
                or (read_layered_scalar(_graph_of(node), 'NODE_PLACEMENT_STRATEGY', 'NODE_PLACEMENT_STRATEGY_0') == 'NETWORK_SIMPLEX'
                    and get_node_flexibility(node) in ('NODE_SIZE_WHERE_SPACE_PERMITS', 'NODE_SIZE'))):
            raw['width'], raw['height'] = node.size.x, node.size.y
        for port in node.ports:
            origin = port.properties.get('ORIGIN')
            if self.state.kinds.get(id(origin)) == 'port':
                origin['x'], origin['y'] = port.pos.x, port.pos.y
                self.state.set_option(origin, 'port.side', port.side)
        from .native_adapters import _read_property
        node_has_placement = bool(_read_property(node, 'NODE_LABELS_PLACEMENT'))
        for label in node.labels:
            if node_has_placement or _read_property(label, 'NODE_LABELS_PLACEMENT'):
                origin = label.properties.get('ORIGIN')
                origin.update(width=label.size.x, height=label.size.y, x=label.pos.x, y=label.pos.y)
        placement = _read_property(node, 'PORT_LABELS_PLACEMENT')
        if 'INSIDE' in placement or 'OUTSIDE' in placement:
            for port in node.ports:
                for label in port.labels:
                    origin = label.properties.get('ORIGIN')
                    origin['width'], origin['height'] = label.size.x, label.size.y
                    origin['x'], origin['y'] = label.pos.x, label.pos.y

    def hierarchical_offset(self, edge):
        target = edge.properties.get('COORDINATE_SYSTEM_ORIGIN')
        if target is None:
            return _ZERO_OFFSET
        result = Vec2()
        current = _graph_of(edge.source.owner)
        while current is not target:
            representing = current.parent_node
            current = _graph_of(representing)
            for value in (representing.pos, current.offset):
                result.x += value.x
                result.y += value.y
            result.x += current.padding.left
            result.y += current.padding.top
        return result

    @staticmethod
    def first_edge_section(raw, reset=True, remove_others=True):
        sections = raw.setdefault('sections', [])
        if not sections:
            section = {'startPoint': {'x': 0.0, 'y': 0.0},
                       'endPoint': {'x': 0.0, 'y': 0.0}, 'bendPoints': []}
            sections.append(section)
            return section
        section = sections[0]
        if reset:
            section.setdefault('bendPoints', []).clear()
            section['startPoint'] = {'x': 0.0, 'y': 0.0}
            section['endPoint'] = {'x': 0.0, 'y': 0.0}
        if remove_others:
            while len(sections) > 1:
                sections.pop()
        return section

    @staticmethod
    def apply_vector_chain(chain, section):
        if len(chain) < 2:
            raise ValueError('The vector chain must contain at least a source and a target point.')
        section['startPoint'] = {'x': chain[0].x, 'y': chain[0].y}
        old = section.setdefault('bendPoints', [])
        index = 0
        for point in chain[1:-1]:
            if index == len(old):
                old.append({})
            old[index]['x'], old[index]['y'] = point.x, point.y
            index += 1
        del old[index:]
        section['endPoint'] = {'x': chain[-1].x, 'y': chain[-1].y}

    def apply_edge_layout(self, edge, routing, offset):
        raw = edge.properties.get('ORIGIN')
        if raw is None:
            return
        chain = edge.bend_points
        edge_offset = Vec2(offset.x, offset.y)
        hierarchical = self.hierarchical_offset(edge)
        edge_offset.x += hierarchical.x
        edge_offset.y += hierarchical.y
        if _descendant(edge.target.owner, edge.source.owner):
            source = _sum_vectors(edge.source.pos, edge.source.anchor)
            source.x -= offset.x
            source.y -= offset.y
        else:
            source = _sum_vectors(edge.source.owner.pos, edge.source.pos, edge.source.anchor)
        chain.insert(0, source)
        target = _sum_vectors(edge.target.owner.pos, edge.target.pos, edge.target.anchor)
        target_offset = edge.properties.get('TARGET_OFFSET')
        if target_offset is not None:
            target.x += target_offset.x
            target.y += target_offset.y
        chain.append(target)
        for point in chain:
            point.x += edge_offset.x
            point.y += edge_offset.y
        section = self.first_edge_section(raw)
        section['incomingShape'], section['outgoingShape'] = raw['sources'][0], raw['targets'][0]
        self.apply_vector_chain(chain, section)
        for label in edge.labels:
            origin = label.properties.get('ORIGIN')
            origin['width'], origin['height'] = label.size.x, label.size.y
            origin['x'], origin['y'] = label.pos.x + edge_offset.x, label.pos.y + edge_offset.y
            include = label.properties.get(_INCLUDE_LABEL)
            if include is None:
                include = False
            if type(include) is not bool:
                raise TypeError('Actual INCLUDE_LABEL Boolean required')
            self._set_include_label(origin, include)
        junctions = get_junction_points(edge)
        if junctions is not None:
            for point in junctions:
                point.x += edge_offset.x
                point.y += edge_offset.y
        self.state.set_option(raw, 'junctionPoints', junctions)
        self.state.set_option(raw, 'edgeRouting', 'SPLINES' if routing == 'SPLINES' else None)

    def _set_include_label(self, raw, value):
        # An actual private Property id, not a public metadata/option alias.
        self.state.set_stored_property(raw, _INCLUDE_LABEL, value)

    def apply_parent_node_layout(self, graph):
        raw = graph.properties.get('ORIGIN')
        included_port_labels = 'PORT_LABELS' in self.reader.get(raw, 'node', 'nodeSize.constraints')
        if getattr(graph, 'parent_node', None) is None:
            properties = graph.properties['GRAPH_PROPERTIES']
            width = graph.size.x + graph.padding.left + graph.padding.right
            height = graph.size.y + graph.padding.top + graph.padding.bottom
            if 'EXTERNAL_PORTS' in properties:
                self.state.set_option(raw, 'portConstraints', 'FIXED_POS')
                self.resize_node(raw, width, height, False, True)
            elif not self.state.read_owner_scalar_property(raw, 'LayeredOptions', 'NODE_SIZE_FIXED_GRAPH_SIZE_0'):
                self.resize_node(raw, width, height, True, True)
        # createFrom builds an EMPTY enum storage array; universe != members.
        self.state.set_option(raw, 'nodeSize.constraints', {'PORT_LABELS'} if included_port_labels else set())

    def effective_minimum_size(self, raw):
        if 'MINIMUM_SIZE' in self.reader.get(raw, 'node', 'nodeSize.constraints'):
            options = self.reader.get(raw, 'node', 'nodeSize.options')
            value = self.reader.get(raw, 'node', 'nodeSize.minimum')
            minimum = Vec2(value.x, value.y)
            if 'DEFAULT_MINIMUM_SIZE' in options:
                if minimum.x <= 0:
                    minimum.x = 20.0
                if minimum.y <= 0:
                    minimum.y = 20.0
            return minimum
        return Vec2()

    def resize_node(self, raw, width, height, move_ports, move_labels):
        old = Vec2(raw['width'], raw['height'])
        new = self.effective_minimum_size(raw)
        new.x, new.y = _maximum(new.x, width), _maximum(new.y, height)
        wr, hr = _divide(new.x, old.x), _divide(new.y, old.y)
        wd, hd = new.x - old.x, new.y - old.y
        if move_ports:
            parent = self.state.parents[id(raw)]
            direction = self.reader.get(raw if parent is None else parent, 'node', 'direction')
            fixed = self.reader.get(raw, 'node', 'portConstraints') == 'FIXED_POS'
            for port in raw.get('ports', []):
                side = self.reader.get(port, 'port', 'port.side')
                if side == 'UNDEFINED':
                    side = _port_side(port, raw, direction)
                    self.state.set_option(port, 'port.side', side)
                if side == 'NORTH':
                    if not fixed:
                        port['x'] *= wr
                elif side == 'EAST':
                    port['x'] += wd
                    if not fixed:
                        port['y'] *= hr
                elif side == 'SOUTH':
                    if not fixed:
                        port['x'] *= wr
                    port['y'] += hd
                elif side == 'WEST' and not fixed:
                    port['y'] *= hr
        raw['width'], raw['height'] = new.x, new.y
        if move_labels:
            for label in raw.get('labels', []):
                mx, my = label['x'] + label['width'] / 2, label['y'] + label['height'] / 2
                wp, hp = _divide(mx, old.x), _divide(my, old.y)
                if wp + hp >= 1:
                    if wp - hp > 0 and my >= 0:
                        label['x'] += wd
                        label['y'] += hd * hp
                    elif wp - hp < 0 and mx >= 0:
                        label['x'] += wd * wp
                        label['y'] += hd
        self.state.set_option(raw, 'nodeSize.constraints', set())
        return Vec2(wr, hr)

    @staticmethod
    def external_port_position(graph, dummy, port_width, port_height):
        position = Vec2(dummy.pos.x, dummy.pos.y)
        position.x += dummy.size.x / 2
        position.y += dummy.size.y / 2
        offset = read_layered_scalar(dummy, 'PORT_BORDER_OFFSET', 'PORT_BORDER_OFFSET')
        size, padding, delta = graph.size, graph.padding, graph.offset
        side = dummy.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
        if side == 'NORTH':
            position.x += padding.left + delta.x - port_width / 2
            position.y = -port_height - offset
            dummy.pos.y = -(padding.top + offset + delta.y)
        elif side == 'EAST':
            position.x = size.x + padding.left + padding.right + offset
            position.y += padding.top + delta.y - port_height / 2
            dummy.pos.x = size.x + padding.right + offset - delta.x
        elif side == 'SOUTH':
            position.x += padding.left + delta.x - port_width / 2
            position.y = size.y + padding.top + padding.bottom + offset
            dummy.pos.y = size.y + padding.bottom + offset - delta.y
        elif side == 'WEST':
            position.x = -port_width - offset
            position.y += padding.top + delta.y - port_height / 2
            dummy.pos.x = -(padding.left + offset + delta.x)
        return position
