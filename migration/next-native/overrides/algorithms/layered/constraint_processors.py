# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Worker275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# P18B in references/e13-kernel-sources.json; native ordered graph views.
"""Actual edge/layer-constraint reversal, including fixed opposite ports."""
from ...execution.diagnostics import BasicProgressMonitor
from .cycles import _boolean
from .cycles_general import reverse_edge
from .ports import is_side_fixed
from .property_access import read_layered_scalar


def _layer_constraint(node):
    return read_layered_scalar(node, 'LAYERING_LAYER_CONSTRAINT', 'LAYERING_LAYER_CONSTRAINT_0')


def can_reverse_incoming_edge(target_constraint, edge):
    if _boolean(edge.properties, 'REVERSED'):
        return False
    source = edge.source.owner
    if target_constraint == 'FIRST' and source.type == 'LABEL':
        return False
    return _layer_constraint(source) != 'FIRST_SEPARATE'


def can_reverse_outgoing_edge(source_constraint, edge):
    if _boolean(edge.properties, 'REVERSED'):
        return False
    target = edge.target.owner
    if source_constraint == 'LAST' and target.type == 'LABEL':
        return False
    return _layer_constraint(target) != 'LAST_SEPARATE'


def reverse_edges(node, node_constraint, target_port_type):
    for port in list(node.ports):
        if target_port_type in ('INPUT', 'UNDEFINED'):
            for edge in list(port.outgoing_edges):
                if can_reverse_outgoing_edge(node_constraint, edge):
                    reverse_edge(edge, adapt_ports=True)
        if target_port_type in ('OUTPUT', 'UNDEFINED'):
            # The source takes this snapshot after outgoing reversals, not at
            # the start of the port iteration.
            for edge in list(port.incoming_edges):
                if can_reverse_incoming_edge(node_constraint, edge):
                    reverse_edge(edge, adapt_ports=True)


def _selected_edge_constraint(layer_constraint):
    if layer_constraint in ('FIRST', 'FIRST_SEPARATE'):
        return 'OUTGOING_ONLY'
    if layer_constraint in ('LAST', 'LAST_SEPARATE'):
        return 'INCOMING_ONLY'
    return None


def _apply_outer_constraint(node, layer_constraint, edge_constraint):
    # Fixed worker literally writes OUTGOING_ONLY in the INCOMING_ONLY case
    # too. The local variable still chooses which adjacency to reverse.
    node.properties['EDGE_CONSTRAINT'] = 'OUTGOING_ONLY'
    if edge_constraint == 'INCOMING_ONLY':
        reverse_edges(node, layer_constraint, 'INPUT')
    elif edge_constraint == 'OUTGOING_ONLY':
        reverse_edges(node, layer_constraint, 'OUTPUT')


def handle_outer_nodes(graph):
    remaining = []
    for node in graph.layerless_nodes:
        constraint = _layer_constraint(node)
        edge_constraint = _selected_edge_constraint(constraint)
        if edge_constraint is not None:
            _apply_outer_constraint(node, constraint, edge_constraint)
        else:
            remaining.append(node)
    return remaining


def handle_inner_nodes(remaining):
    for node in remaining:
        constraint = _layer_constraint(node)
        edge_constraint = _selected_edge_constraint(constraint)
        if edge_constraint is not None:
            _apply_outer_constraint(node, constraint, edge_constraint)
        elif is_side_fixed(read_layered_scalar(node, 'PORT_CONSTRAINTS', 'PORT_CONSTRAINTS_0')) and node.ports:
            all_reversed = True
            for port in node.ports:
                if not (port.side == 'EAST' and len(port.incoming_edges) - len(port.outgoing_edges) > 0
                        or port.side == 'WEST' and len(port.incoming_edges) - len(port.outgoing_edges) < 0):
                    all_reversed = False
                    break
                for edge in port.outgoing_edges:
                    if _layer_constraint(edge.target.owner) in ('LAST', 'LAST_SEPARATE'):
                        all_reversed = False
                        break
                # A false flag does not skip this read, or subsequent ports.
                for edge in port.incoming_edges:
                    if _layer_constraint(edge.source.owner) in ('FIRST', 'FIRST_SEPARATE'):
                        all_reversed = False
                        break
            if all_reversed:
                reverse_edges(node, constraint, 'UNDEFINED')


def edge_and_layer_constraint_edge_reverser(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Edge and layer constraint edge reversal', 1)
    remaining = handle_outer_nodes(graph)
    handle_inner_nodes(remaining)
    monitor.done()


# P18C: actual class-local Property id; not an invented public option or alias.
_SEPARATE_CONNECTIONS = 'separateLayerConnections'


def _connected_edges(node):
    # The getter first captures each current port's two live iterable objects.
    # CombineIter.next rechecks the incoming cursor every time; restoring an
    # incoming edge while consuming outgoing can therefore revive the first.
    iterables = [(port.incoming_edges, port.outgoing_edges) for port in node.ports]
    for incoming, outgoing in iterables:
        first = second = 0
        while first < len(incoming) or second < len(outgoing):
            if first < len(incoming):
                edge = incoming[first]
                first += 1
            else:
                edge = outgoing[second]
                second += 1
            yield edge


def _directed_edges(node, incoming):
    iterables = [port.incoming_edges if incoming else port.outgoing_edges for port in node.ports]
    for edges in iterables:
        index = 0
        while index < len(edges):
            edge = edges[index]
            index += 1
            yield edge


def _designation(node):
    from .diagnostic_strings import node_designation
    graph = node.graph if node.graph is not None else node.layer.graph
    value = node_designation(node, getattr(graph, '_source_session', None))
    return 'null' if value is None else str(value)


def _configuration_error(message):
    from ..._errors import UnsupportedFeatureError
    raise UnsupportedFeatureError('UNSUPPORTED_CONFIGURATION', '', message)


def _acceptable_incident_edge(edge):
    return edge.source.owner.type == 'EXTERNAL_PORT' and edge.target.owner.type == 'EXTERNAL_PORT'


def _ensure_acceptable_edges(node):
    constraint = _layer_constraint(node)
    if constraint == 'FIRST_SEPARATE':
        for edge in _directed_edges(node, True):
            if not _acceptable_incident_edge(edge):
                _configuration_error("Node '" + _designation(node)
                    + "' has its layer constraint set to FIRST_SEPARATE, but has at least one incoming edge. "
                    + 'FIRST_SEPARATE nodes must not have incoming edges.')
    elif constraint == 'LAST_SEPARATE':
        for edge in _directed_edges(node, False):
            if not _acceptable_incident_edge(edge):
                _configuration_error("Node '" + _designation(node)
                    + "' has its layer constraint set to LAST_SEPARATE, but has at least one outgoing edge. "
                    + 'LAST_SEPARATE nodes must not have outgoing edges.')


def _combine_separate_connections(previous, constraint):
    first = constraint == 'FIRST_SEPARATE'
    if previous == 'NONE':
        return 'FIRST_SEPARATE' if first else 'LAST_SEPARATE'
    if previous == 'FIRST_SEPARATE':
        return 'FIRST_SEPARATE' if first else 'BOTH'
    if previous == 'LAST_SEPARATE':
        return 'BOTH' if first else 'LAST_SEPARATE'
    return 'BOTH'


def _update_opposite_constraints(hidden, opposite):
    if 'LAYERING_LAYER_CONSTRAINT' in opposite.properties:
        return
    previous = opposite.properties.get(_SEPARATE_CONNECTIONS, 'NONE')
    connections = _combine_separate_connections(previous, _layer_constraint(hidden))
    opposite.properties[_SEPARATE_CONNECTIONS] = connections
    if next(_connected_edges(opposite), None) is not None:
        return
    if connections == 'FIRST_SEPARATE':
        opposite.properties['LAYERING_LAYER_CONSTRAINT'] = 'FIRST'
    elif connections == 'LAST_SEPARATE':
        opposite.properties['LAYERING_LAYER_CONSTRAINT'] = 'LAST'


def _hide_node(node):
    from .graph import set_source, set_target
    _ensure_acceptable_edges(node)
    for edge in _connected_edges(node):
        outgoing = edge.source.owner is node
        opposite = edge.target if outgoing else edge.source
        if outgoing:
            set_target(edge, None)
        else:
            set_source(edge, None)
        edge.properties['ORIGINAL_OPPOSITE_PORT'] = opposite
        _update_opposite_constraints(node, opposite.owner)


def layer_constraint_preprocessor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Layer constraint preprocessing', 1)
    hidden = []
    index = 0
    while index < len(graph.layerless_nodes):
        node = graph.layerless_nodes[index]
        index += 1
        if _layer_constraint(node) in ('FIRST_SEPARATE', 'LAST_SEPARATE'):
            _hide_node(node)
            hidden.append(node)
            graph.layerless_nodes.pop(index - 1)
            index -= 1
    if hidden:
        graph.properties['HIDDEN_NODES'] = hidden
    monitor.done()


def _validate_first(node):
    for edge in _directed_edges(node, True):
        if edge.source.owner.type != 'LABEL':
            _configuration_error("Node '" + _designation(node)
                + "' has its layer constraint set to FIRST, but has at least one incoming edge that "
                + ' does not come from a FIRST_SEPARATE node. That must not happen.')


def _validate_last(node):
    for edge in _directed_edges(node, False):
        if edge.target.owner.type != 'LABEL':
            _configuration_error("Node '" + _designation(node)
                + "' has its layer constraint set to LAST, but has at least one outgoing edge that "
                + ' does not go to a LAST_SEPARATE node. That must not happen.')


def _move_labels(node, incoming, label_layer):
    from .graph import set_layer
    for edge in _directed_edges(node, incoming):
        other = edge.source.owner if incoming else edge.target.owner
        if other.type == 'LABEL':
            set_layer(other, label_layer)


def _move_first_last_nodes(graph, first, last, first_labels, last_labels):
    from .graph import set_layer
    for layer in graph.layers:
        for node in list(layer.nodes):
            constraint = _layer_constraint(node)
            if constraint == 'FIRST':
                _validate_first(node)
                set_layer(node, first)
                _move_labels(node, True, first_labels)
            elif constraint == 'LAST':
                _validate_last(node)
                set_layer(node, last)
                _move_labels(node, False, last_labels)
    index = 0
    while index < len(graph.layers):
        if not graph.layers[index].nodes:
            graph.layers.pop(index)
        else:
            index += 1


def _restore_hidden_nodes(graph, first, last):
    from .graph import set_layer, set_source, set_target
    for node in graph.properties['HIDDEN_NODES']:
        constraint = _layer_constraint(node)
        if constraint == 'FIRST_SEPARATE':
            set_layer(node, first)
        elif constraint == 'LAST_SEPARATE':
            set_layer(node, last)
        for edge in _connected_edges(node):
            if edge.source is not None and edge.target is not None:
                continue
            outgoing = edge.target is None
            opposite = edge.properties.get('ORIGINAL_OPPOSITE_PORT')
            if outgoing:
                set_target(edge, opposite)
            else:
                set_source(edge, opposite)


def layer_constraint_postprocessor(graph, *, monitor=None):
    from .graph import Layer
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Layer constraint postprocessing', 1)
    if graph.layers:
        first, last = graph.layers[0], graph.layers[-1]
        first_labels, last_labels = Layer(graph), Layer(graph)
        _move_first_last_nodes(graph, first, last, first_labels, last_labels)
        if first_labels.nodes:
            graph.layers.insert(0, first_labels)
        if last_labels.nodes:
            graph.layers.append(last_labels)
    if 'HIDDEN_NODES' in graph.properties:
        first, last = Layer(graph), Layer(graph)
        _restore_hidden_nodes(graph, first, last)
        if first.nodes:
            graph.layers.insert(0, first)
        if last.nodes:
            graph.layers.append(last)
    monitor.done()
