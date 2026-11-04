# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P15A in references/e13-kernel-sources.json.
# Native typed raw/identity/container view; no generic collection runtime copied.
"""Actual eager Layered strings over native labels and raw-origin ownership."""


def _registered(state, element):
    return state is not None and id(element) in state.kinds


def _container(state, element):
    if state.kinds[id(element)] == 'edge':
        return state.current_containers[id(element)]
    return state.json_parents[id(element)]


def get_identifier(state, element):
    parts = []
    while _registered(state, element):
        identifier = state.identifier_text(element)
        if not identifier:
            break
        parts.append(identifier)
        element = _container(state, element)
    return '.'.join(reversed(parts)) if parts else None


def get_origin_identifier(element, state=None):
    origin = element.properties.get('ORIGIN')
    if state is None and type(origin) is dict:
        raise TypeError('Actual JsonLayoutSession is required for a raw origin')
    return get_identifier(state, origin) if _registered(state, origin) else None


def _index(items, value):
    for index, item in enumerate(items):
        if item is value:
            return index
    return -1


def _designation(element, state):
    labels = getattr(element, 'labels', ())
    if labels and getattr(labels[0], 'text', ''):
        return labels[0].text
    return get_origin_identifier(element, state)


def node_designation(node, state=None):
    result = _designation(node, state)
    return result if result is not None else str(-1 if node.layer is None else _index(node.layer.nodes, node))


def port_designation(port, state=None):
    result = _designation(port, state)
    return result if result is not None else str(-1 if port.owner is None else _index(port.owner.ports, port))


def node_text(node, state=None):
    if node is None:
        return 'null'
    return 'n' + ('' if node.type == 'NORMAL' else '(' + node.type.lower() + ')') + '_' + node_designation(node, state)


def port_text(port, state=None):
    if port is None:
        return 'null'
    result = 'p_' + port_designation(port, state)
    if port.owner is not None:
        result += '[' + node_text(port.owner, state) + ']'
    if len(port.incoming_edges) == 1 and not port.outgoing_edges and port.incoming_edges[0].source is not port:
        source = port.incoming_edges[0].source
        result += ' << ' + port_designation(source, state) + '[' + node_text(source.owner, state) + ']'
    if not port.incoming_edges and len(port.outgoing_edges) == 1 and port.outgoing_edges[0].target is not port:
        target = port.outgoing_edges[0].target
        result += ' >> ' + port_designation(target, state) + '[' + node_text(target.owner, state) + ']'
    return result


def node_list_text(nodes, state=None):
    return '[' + ', '.join(node_text(node, state) for node in nodes) + ']'


def port_list_text(ports, state=None):
    return '[' + ', '.join(port_text(port, state) for port in ports) + ']'


def layer_text(layer, state=None):
    return 'L_' + str(_index(layer.graph.layers, layer)) + node_list_text(layer.nodes, state)
