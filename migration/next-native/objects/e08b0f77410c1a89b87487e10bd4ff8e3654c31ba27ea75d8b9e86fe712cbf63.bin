# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P21B/C actual compound preprocessing.
"""Real cross-level edge segmentation and post-order hierarchy preparation."""
from dataclasses import dataclass

from ..disco import _IdentityMap
from ...execution.identity import identity_hash
from .cell_layout import _maximum
from .compound_model import CrossHierarchyEdge, CrossHierarchyEdgeComparator, IdentityMultimap
from .external_port_dummy import FROM_DIRECTION, OPPOSED, create_external_port_dummy
from .graph import LEdge, LPort, Vec2, set_port_owner, set_source, set_target
from .graph_configurator import _graph_of, get_direction
from .native_import import LLabel
from .native_adapters import _read_property
from .native_properties import CanonicalPropertyMap
from .native_transfer import _descendant
from .node_size_cells import compute_inside_part
from .ports import _source_sort, is_side_fixed, set_side
from .property_access import read_layered_scalar


def _read(holder, key, symbol=None):
    if key == 'PORT_LABELS_PLACEMENT':
        # This Layered alias is the actual Core non-type4 shared EnumSet.
        # It is a structured owner default, not a scalar/metadata fallback.
        return _read_property(holder, 'org.eclipse.elk.portLabels.placement')
    return read_layered_scalar(holder, key, key if symbol is None else symbol)


def _contains(items, item):
    return any(value is item for value in items)


def _self_loop(edge):
    return edge.source.owner is edge.target.owner


def create_dummy_edge(original):
    edge = LEdge(properties=CanonicalPropertyMap(
        original.properties, getattr(original, 'integer_box_identities', {})))
    edge.integer_box_identities = edge.properties.integer_boxes
    edge.labels = []
    # All other stored values, including ORIGIN, retain the same object refs.
    edge.properties['JUNCTION_POINTS'] = None
    return edge


@dataclass(eq=False)
class ExternalPort:
    new_edge: object
    dummy_node: object
    dummy_port: object
    type: str
    exported: bool
    orig_edges: list

    @classmethod
    def create(cls, original, edge, node, port, port_type, exported):
        return cls(edge, node, port, port_type, exported, [original])


class _PropertyHolder:
    def __init__(self):
        self.properties = CanonicalPropertyMap()


def calculate_net_flow(port):
    node = port.owner
    enabled = _read(node, 'INSIDE_SELF_LOOPS_ACTIVATE')
    output_vote = input_vote = 0.0
    for edge in port.outgoing_edges:
        loop = _self_loop(edge)
        inside = loop and enabled and _read(edge, 'INSIDE_SELF_LOOPS_YO')
        target = edge.target.owner
        if loop and inside:
            input_vote += 1
        elif loop and not inside:
            output_vote += 1
        elif getattr(_graph_of(target), 'parent_node', None) is node:
            input_vote += 1
        else:
            output_vote += 1
    for edge in port.incoming_edges:
        loop = _self_loop(edge)
        inside = loop and enabled and _read(edge, 'INSIDE_SELF_LOOPS_YO')
        source = edge.source.owner
        if loop and inside:
            output_vote += 1
        elif loop and not inside:
            input_vote += 1
        elif getattr(_graph_of(source), 'parent_node', None) is node:
            output_vote += 1
        else:
            input_vote += 1
    return output_vote - input_vote


def create_port_for_dummy(dummy, parent, port_type):
    graph = _graph_of(parent)
    direction = get_direction(graph)
    port = LPort(properties=CanonicalPropertyMap())
    port.integer_box_identities = port.properties.integer_boxes
    port.labels = []
    set_port_owner(port, parent)
    if port_type == 'INPUT':
        set_side(port, OPPOSED[FROM_DIRECTION[direction]])
    elif port_type == 'OUTPUT':
        set_side(port, FROM_DIRECTION[direction])
    port.properties['PORT_BORDER_OFFSET'] = _read(dummy, 'PORT_BORDER_OFFSET')
    return port


def get_shallowest_edge_segment(segments):
    result = -1
    for index, segment in enumerate(segments):
        if segment.type == 'INPUT':
            result = 0 if index == 0 else index - 1
            break
        elif index == len(segments) - 1:
            result = index
    return result


class CompoundGraphPreprocessor:
    def __init__(self):
        self._identity_owner = None
        self.dummy_node_map = _IdentityMap(self)
        self.cross_hierarchy_map = None

    def identity_hash(self, value):
        method = getattr(self._identity_owner, 'identity_hash', None)
        return method(value) if method is not None else identity_hash(self, value)

    def connect_child(self, graph, external, original, source, target):
        edge = create_dummy_edge(original)
        set_source(edge, source)
        set_target(edge, target)
        self.cross_hierarchy_map.put(original, CrossHierarchyEdge(edge, graph, external.type))

    def connect_siblings(self, graph, output, contained, original):
        target = None
        for external in contained:
            if external is not output and _contains(external.orig_edges, original):
                target = external
                break
        edge = create_dummy_edge(original)
        set_source(edge, output.dummy_port)
        set_target(edge, target.dummy_port)
        self.cross_hierarchy_map.put(original, CrossHierarchyEdge(edge, graph, output.type))

    def create_external_dummy(self, graph, parent, port_type, side, edge):
        outside = edge.source if port_type == 'INPUT' else edge.target
        direction = get_direction(graph)
        if outside.owner is parent:
            dummy = self.dummy_node_map.get(outside)
            if dummy is None:
                dummy = create_external_port_dummy(outside, _read(parent, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0'),
                    side, calculate_net_flow(outside), None, outside.pos, outside.size, direction, graph)
                dummy.properties['ORIGIN'] = outside
                self.dummy_node_map.put(outside, dummy)
        else:
            holder = _PropertyHolder()
            holder.properties['PORT_BORDER_OFFSET'] = _read(graph, 'SPACING_EDGE_EDGE') / 2
            dummy = create_external_port_dummy(holder, _read(parent, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0'),
                side, -1 if port_type == 'INPUT' else 1, None, Vec2(), Vec2(), direction, graph)
            port = create_port_for_dummy(dummy, parent, port_type)
            dummy.properties['ORIGIN'] = port
            self.dummy_node_map.put(port, dummy)
        graph.properties['GRAPH_PROPERTIES'].add('EXTERNAL_PORTS')
        graph.properties['PORT_CONSTRAINTS'] = ('FIXED_SIDE' if is_side_fixed(
            _read(graph, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')) else 'FREE')
        return dummy

    def introduce_segment(self, graph, parent, original, opposite, port_type, default):
        merge = _read(graph, 'MERGE_HIERARCHY_EDGES', 'MERGE_HIERARCHY_EDGES_0')
        parent_end = None
        if port_type == 'INPUT' and original.source.owner is parent:
            parent_end = original.source
        elif port_type == 'OUTPUT' and original.target.owner is parent:
            parent_end = original.target
        external = default
        if external is None or not merge or parent_end is not None:
            side = 'UNDEFINED'
            if parent_end is not None:
                side = parent_end.side
            elif is_side_fixed(_read(parent, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')):
                side = 'WEST' if port_type == 'INPUT' else 'EAST'
            dummy = self.create_external_dummy(graph, parent, port_type, side, original)
            _graph_of(parent)  # Source evaluates this even though its result is unused.
            edge = create_dummy_edge(original)
            if port_type == 'INPUT':
                set_source(edge, dummy.ports[0])
                set_target(edge, opposite)
            else:
                set_source(edge, opposite)
                set_target(edge, dummy.ports[0])
            external = ExternalPort.create(original, edge, dummy, dummy.properties.get('ORIGIN'),
                                            port_type, parent_end is None)
        else:
            external.orig_edges.append(original)
            thickness = _maximum(_read(external.new_edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0'),
                                 _read(original, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0'))
            external.new_edge.properties['EDGE_THICKNESS'] = thickness
        self.cross_hierarchy_map.put(original, CrossHierarchyEdge(external.new_edge, graph, port_type))
        return external

    @staticmethod
    def _register_created(graph, created, exported):
        for external in created:
            if not _contains(graph.layerless_nodes, external.dummy_node):
                graph.layerless_nodes.append(external.dummy_node)
            if external.exported:
                exported.append(external)

    def process_inner_segments(self, graph, parent, contained, exported):
        created = []
        for external in contained:
            current = None
            if external.type == 'OUTPUT':
                for edge in external.orig_edges:
                    target = edge.target.owner
                    if _graph_of(target) is graph:
                        self.connect_child(graph, external, edge, external.dummy_port, edge.target)
                    elif parent is None or _descendant(target, parent):
                        self.connect_siblings(graph, external, contained, edge)
                    else:
                        new = self.introduce_segment(graph, parent, edge, external.dummy_port, 'OUTPUT', current)
                        if new is not current:
                            created.append(new)
                        if new.exported:
                            current = new
            else:
                for edge in external.orig_edges:
                    source = edge.source.owner
                    if _graph_of(source) is graph:
                        self.connect_child(graph, external, edge, edge.source, external.dummy_port)
                    elif parent is None or _descendant(source, parent):
                        continue
                    else:
                        new = self.introduce_segment(graph, parent, edge, external.dummy_port, 'INPUT', current)
                        if new is not current:
                            created.append(new)
                        if new.exported:
                            current = new
        self._register_created(graph, created, exported)

    def process_outer_segments(self, graph, parent, exported):
        created = []
        for child in graph.layerless_nodes:
            for port in child.ports:
                current_output = None
                for edge in list(port.outgoing_edges):
                    if not _descendant(edge.target.owner, parent):
                        new = self.introduce_segment(graph, parent, edge, edge.source, 'OUTPUT', current_output)
                        if new is not current_output:
                            created.append(new)
                        if new.exported:
                            current_output = new
                current_input = None
                for edge in list(port.incoming_edges):
                    if not _descendant(edge.source.owner, parent):
                        new = self.introduce_segment(graph, parent, edge, edge.target, 'INPUT', current_input)
                        if new is not current_input:
                            created.append(new)
                        if new.exported:
                            current_input = new
        self._register_created(graph, created, exported)

    def process_inside_self_loops(self, nested, node):
        if not _read(node, 'INSIDE_SELF_LOOPS_ACTIVATE'):
            return
        for port in node.ports:
            for original in list(port.outgoing_edges):
                loop = original.target.owner is node
                inside = loop and _read(original, 'INSIDE_SELF_LOOPS_YO')
                if inside:
                    source = original.source
                    source_dummy = self.dummy_node_map.get(source)
                    if source_dummy is None:
                        source_dummy = create_external_port_dummy(source, 'FREE', source.side, -1, None,
                            None, source.size, _read(nested, 'DIRECTION'), nested)
                        source_dummy.properties['ORIGIN'] = source
                        self.dummy_node_map.put(source, source_dummy)
                        nested.layerless_nodes.append(source_dummy)
                    target = original.target
                    target_dummy = self.dummy_node_map.get(target)
                    if target_dummy is None:
                        target_dummy = create_external_port_dummy(target, 'FREE', target.side, 1, None,
                            None, target.size, _read(nested, 'DIRECTION'), nested)
                        target_dummy.properties['ORIGIN'] = target
                        self.dummy_node_map.put(target, target_dummy)
                        nested.layerless_nodes.append(target_dummy)
                    edge = create_dummy_edge(original)
                    set_source(edge, source_dummy.ports[0])
                    set_target(edge, target_dummy.ports[0])
                    self.cross_hierarchy_map.put(original, CrossHierarchyEdge(edge, nested, 'OUTPUT'))
                    nested.properties['GRAPH_PROPERTIES'].add('EXTERNAL_PORTS')

    def _transform_steps(self, graph, parent):
        contained = []
        for node in graph.layerless_nodes:
            nested = getattr(node, 'nested_graph', None)
            if nested is not None:
                child_ports = yield nested, node
                contained.extend(child_ports)
                self.process_inside_self_loops(nested, node)
                if 'EXTERNAL_PORTS' in nested.properties['GRAPH_PROPERTIES']:
                    constraints = _read(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
                    inside_labels = 'INSIDE' in _read(node, 'PORT_LABELS_PLACEMENT', 'PORT_LABELS_PLACEMENT_1')
                    for port in node.ports:
                        dummy = self.dummy_node_map.get(port)
                        if dummy is None:
                            dummy = create_external_port_dummy(port, constraints, port.side,
                                -(len(port.incoming_edges) - len(port.outgoing_edges)), None,
                                Vec2(), port.size, _read(nested, 'DIRECTION'), nested)
                            dummy.properties['ORIGIN'] = port
                            self.dummy_node_map.put(port, dummy)
                            nested.layerless_nodes.append(dummy)
                        dummy_port = dummy.ports[0]
                        for label in port.labels:
                            dummy_label = LLabel()
                            dummy_label.size.x, dummy_label.size.y = label.size.x, label.size.y
                            dummy_port.labels.append(dummy_label)
                            if not inside_labels:
                                side = port.side
                                inside_part = 0.0
                                placement = _read(node, 'PORT_LABELS_PLACEMENT', 'PORT_LABELS_PLACEMENT_1')
                                if 'INSIDE' not in placement and 'OUTSIDE' not in placement:
                                    inside_part = compute_inside_part(label.pos, label.size, port.size, 0, side)
                                if constraints == 'FREE' or side in ('EAST', 'WEST'):
                                    dummy_label.size.x = inside_part
                                else:
                                    dummy_label.size.y = inside_part
        exported = []
        self.process_inner_segments(graph, parent, contained, exported)
        if parent is not None:
            self.process_outer_segments(graph, parent, exported)
        return exported

    def transform_hierarchy_edges(self, graph, parent):
        # Explicit generator continuations preserve recursive source return order.
        stack = [self._transform_steps(graph, parent)]
        returned = None
        while stack:
            try:
                nested, node = stack[-1].send(returned)
                returned = None
                stack.append(self._transform_steps(nested, node))
            except StopIteration as done:
                returned = done.value
                stack.pop()
        return returned

    def move_labels_and_remove_original_edges(self, graph):
        for original in self.cross_hierarchy_map.keys():
            if len(original.labels) > 0:
                segments = list(self.cross_hierarchy_map.values_for(original))
                _source_sort(segments, CrossHierarchyEdgeComparator(graph).compare)
                index = 0
                while index < len(original.labels):
                    label = original.labels[index]
                    selected = -1
                    placement = _read(label, 'EDGE_LABELS_PLACEMENT')
                    if placement == 'HEAD':
                        selected = len(segments) - 1
                    elif placement == 'CENTER':
                        selected = get_shallowest_edge_segment(segments)
                    elif placement == 'TAIL':
                        selected = 0
                    if selected != -1:
                        segment = segments[selected]
                        segment.new_edge.labels.append(label)
                        _graph_of(segment.new_edge.source.owner).properties['GRAPH_PROPERTIES'].add('END_LABELS')
                        _graph_of(segment.new_edge.source.owner).properties['GRAPH_PROPERTIES'].add('CENTER_LABELS')
                        original.labels.pop(index)
                        label.properties['ORIGINAL_LABEL_EDGE'] = original
                    else:
                        index += 1
            set_source(original, None)
            set_target(original, None)

    def set_sides_of_ports_to_sides_of_dummy_nodes(self):
        for port, dummy in self.dummy_node_map.items():
            dummy.properties['ORIGIN'] = port
            port.properties['PORT_DUMMY'] = dummy
            port.properties['INSIDE_CONNECTIONS'] = True
            set_side(port, dummy.properties.get('EXT_PORT_SIDE', 'UNDEFINED'))
            dummy.properties.get('EXT_PORT_SIDE', 'UNDEFINED')
            port.owner.properties['PORT_CONSTRAINTS'] = 'FIXED_SIDE'
            _graph_of(port.owner).properties['GRAPH_PROPERTIES'].add('NON_FREE_PORTS')

    def process(self, graph, *, monitor):
        monitor.begin('Compound graph preprocessor', 1)
        self._identity_owner = graph
        self.cross_hierarchy_map = IdentityMultimap(graph)
        self.transform_hierarchy_edges(graph, None)
        self.move_labels_and_remove_original_edges(graph)
        self.set_sides_of_ports_to_sides_of_dummy_nodes()
        graph.properties['CROSS_HIERARCHY_MAP'] = self.cross_hierarchy_map
        self.cross_hierarchy_map = None
        self.dummy_node_map.keys.buckets.clear()
        self.dummy_node_map.values_by_id.clear()
        self._identity_owner = None
        monitor.done()
