# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P22B actual hierarchy port constraints.
"""Actual fixed-order chains and north/south external-dummy replacement."""
from ..disco import _IdentityMap
from ...execution.identity import identity_hash
from .forster_constraints import _successors
from .graph import LNode, LPort, Layer, set_layer, set_port_owner, set_source, set_target
from .native_properties import CanonicalPropertyMap
from .ports import _source_sort, set_side
from .property_access import read_layered_scalar


class _NullAwareHashOwner:
    def __init__(self, graph):
        self.graph = graph

    def identity_hash(self, value):
        if value is None:
            return 0
        method = getattr(self.graph, 'identity_hash', None)
        return method(value) if method is not None else identity_hash(self.graph, value)


def _incoming(node):
    lists = [port.incoming_edges for port in node.ports]
    for edges in lists:
        yield from edges


def _outgoing(node):
    lists = [port.outgoing_edges for port in node.ports]
    for edges in lists:
        yield from edges


def create_dummy(graph, original):
    node = LNode(graph, properties=CanonicalPropertyMap(
        original.properties, getattr(original, 'integer_box_identities', {})))
    node.integer_box_identities = node.properties.integer_boxes
    node.labels = []
    node.properties['EXT_PORT_REPLACED_DUMMY'] = original
    node.properties['PORT_CONSTRAINTS'] = 'FIXED_POS'
    node.properties['ALIGNMENT'] = 'CENTER'
    node.type = 'EXTERNAL_PORT'
    for side in ('WEST', 'EAST'):
        port = LPort(properties=CanonicalPropertyMap())
        port.integer_box_identities = port.properties.integer_boxes
        port.labels = []
        set_port_owner(port, node)
        set_side(port, side)
    return node


def is_northern_or_southern_dummy(node):
    if node.type == 'EXTERNAL_PORT':
        return node.properties.get('EXT_PORT_SIDE', 'UNDEFINED') in ('NORTH', 'SOUTH')
    return False


def compare_nodes(first, second):
    first_type = first.type
    first_position = first.properties.get('PORT_RATIO_OR_POSITION', 0.0)
    second_type = second.type
    second_position = second.properties.get('PORT_RATIO_OR_POSITION', 0.0)
    if second_type != 'EXTERNAL_PORT':
        return -1
    if first_type != 'EXTERNAL_PORT':
        return 1
    if first_position == second_position:
        return 0
    return -1 if first_position < second_position else 1


def process_eastern_and_western_layer(layer):
    nodes = list(layer.nodes)
    _source_sort(nodes, compare_nodes)
    previous = None
    for node in nodes:
        if node.type != 'EXTERNAL_PORT':
            break
        if node.properties.get('EXT_PORT_SIDE', 'UNDEFINED') not in ('WEST', 'EAST'):
            continue
        if previous is not None:
            _successors(previous).append(node)
        previous = node


def process_eastern_and_western_dummies(graph):
    constraints = read_layered_scalar(graph, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
    if constraints not in ('FIXED_ORDER', 'FIXED_RATIO', 'FIXED_POS'):
        return
    layers = graph.layers
    process_eastern_and_western_layer(layers[0])
    process_eastern_and_western_layer(layers[-1])


def process_northern_and_southern_dummies(graph):
    constraints = read_layered_scalar(graph, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')
    if constraints in ('FREE', 'UNDEFINED'):
        return
    layers = graph.layers
    layer_count = len(layers)
    owner = _NullAwareHashOwner(graph)
    maps = [_IdentityMap(owner), _IdentityMap(owner)]
    new_nodes = [[], []]
    originals = []
    for index in range(layer_count):
        layer = layers[index]
        previous_map = maps[index]
        following_map = _IdentityMap(owner)
        maps.append(following_map)
        previous_nodes = new_nodes[index]
        following_nodes = []
        new_nodes.append(following_nodes)
        for node in layer.nodes:
            if is_northern_or_southern_dummy(node):
                originals.append(node)
                continue
            for edge in _incoming(node):
                source = edge.source.owner
                if not is_northern_or_southern_dummy(source):
                    continue
                dummy = previous_map.get(source.properties.get('ORIGIN'))
                if dummy is None:
                    dummy = create_dummy(graph, source)
                    previous_map.put(source.properties.get('ORIGIN'), dummy)
                    previous_nodes.append(dummy)
                set_source(edge, dummy.ports[1])
            for edge in _outgoing(node):
                target = edge.target.owner
                if not is_northern_or_southern_dummy(target):
                    continue
                dummy = following_map.get(target.properties.get('ORIGIN'))
                if dummy is None:
                    dummy = create_dummy(graph, target)
                    following_map.put(target.properties.get('ORIGIN'), dummy)
                    following_nodes.append(dummy)
                set_target(edge, dummy.ports[0])
    for index, nodes in enumerate(new_nodes):
        if len(nodes) == 0:
            continue
        if index == 0:
            layer = Layer(graph)
            layers.insert(0, layer)
        elif index == len(maps) - 1:
            layer = Layer(graph)
            layers.append(layer)
        else:
            layer = layers[index - 1]
        for node in nodes:
            set_layer(node, layer)
    for node in originals:
        set_layer(node, None)
    graph.properties['EXT_PORT_REPLACED_DUMMIES'] = originals


def hierarchical_port_constraints_processor(graph, *, monitor):
    monitor.begin('Hierarchical port constraint processing', 1)
    process_eastern_and_western_dummies(graph)
    process_northern_and_southern_dummies(graph)
    monitor.done()
