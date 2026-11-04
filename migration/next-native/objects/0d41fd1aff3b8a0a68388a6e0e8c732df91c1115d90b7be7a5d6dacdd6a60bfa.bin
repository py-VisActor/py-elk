# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P26C six modes plus exact gathering subset.
"""Actual label-side selection and incident endpoint-label gathering."""
import math

from ...execution.diagnostics import BasicProgressMonitor
from .cell_layout import _maximum
from .center_label_dummies import _all_inline
from .property_access import read_layered_scalar


def _ceil(value):
    if value == 0 or not math.isfinite(value):
        return value
    result = float(math.ceil(value))
    return math.copysign(0.0, value) if result == 0 else result


def _boolean(holder, name):
    value = holder.properties.get(name)
    if value is None:
        value = False
    if type(value) is not bool:
        raise TypeError('Actual internal Boolean property required: ' + name)
    return value


def _outgoing(node):
    for port in node.ports:
        yield from port.outgoing_edges


def _incoming(node):
    for port in node.ports:
        yield from port.incoming_edges


def _incident(port):
    first = second = 0
    while first < len(port.incoming_edges) or second < len(port.outgoing_edges):
        if first < len(port.incoming_edges):
            edge = port.incoming_edges[first]
            first += 1
        else:
            edge = port.outgoing_edges[second]
            second += 1
        yield edge


def gather_labels_from_port(port, target):
    maximum = -1.0
    for edge in _incident(port):
        maximum = _maximum(maximum, read_layered_scalar(
            edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0'))
        placement = 'TAIL' if edge.source is port else 'HEAD'
        labels = [label for label in edge.labels if read_layered_scalar(
            label, 'EDGE_LABELS_PLACEMENT', 'EDGE_LABELS_PLACEMENT') == placement]
        for label in labels:
            if 'END_LABEL_EDGE' not in label.properties:
                label.properties['END_LABEL_EDGE'] = edge
        target.extend(labels)
    return maximum


def gather_labels(port):
    labels = []
    maximum = gather_labels_from_port(port, labels)
    dummy = port.properties.get('PORT_DUMMY')
    if dummy is not None:
        for dummy_port in dummy.ports:
            if dummy_port.properties.get('ORIGIN') is port:
                maximum = _maximum(maximum, gather_labels_from_port(dummy_port, labels))
    if labels:
        port.properties['MAX_EDGE_THICKNESS'] = maximum
    return labels if maximum != -1 else None


def apply_label_side(labels, side):
    for label in labels:
        label.properties['LABEL_SIDE'] = side


def apply_dummy_side(dummy, side):
    if dummy.type != 'LABEL':
        return
    effective = 'INLINE' if _all_inline(dummy.properties.get('REPRESENTED_LABELS')) else side
    dummy.properties['LABEL_SIDE'] = effective
    if effective != 'BELOW':
        edge = dummy.properties.get('ORIGIN')
        thickness = read_layered_scalar(edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0')
        port_y = 0.0
        if effective == 'ABOVE':
            port_y = dummy.size.y - _ceil(thickness / 2)
        elif effective == 'INLINE':
            port_y = _ceil((dummy.size.y - read_layered_scalar(
                dummy.graph, 'SPACING_EDGE_LABEL', 'SPACING_EDGE_LABEL_0')) - thickness) / 2
            dummy.size.y -= read_layered_scalar(
                dummy.graph, 'SPACING_EDGE_LABEL', 'SPACING_EDGE_LABEL_0')
            dummy.size.y -= thickness
        for port in dummy.ports:
            port.pos.y = port_y


def _apply_dummy_run(run, default):
    if run:
        if len(run) == 2:
            apply_dummy_side(run[0], 'ABOVE')
            apply_dummy_side(run[1], 'BELOW')
        else:
            for dummy in run:
                apply_dummy_side(dummy, default)
        run.clear()


def _simple_loop_runs(dummies, default):
    run = []
    previous_source = previous_target = None
    for dummy in dummies:
        source = dummy.properties.get('LONG_EDGE_SOURCE')
        source = None if source is None else source.owner
        target = dummy.properties.get('LONG_EDGE_TARGET')
        target = None if target is None else target.owner
        if previous_source is not source or previous_target is not target:
            _apply_dummy_run(run, default)
            previous_source, previous_target = source, target
        run.append(dummy)
    _apply_dummy_run(run, default)


def _opposite(side):
    return {'ABOVE': 'BELOW', 'BELOW': 'ABOVE', 'INLINE': 'INLINE'}.get(side, 'UNKNOWN')


def _same_side(graph, side):
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type == 'LABEL':
                apply_dummy_side(node, side)
            for edge in _outgoing(node):
                apply_label_side(edge.labels, side)


def _based_on_direction(graph, default):
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type == 'LABEL':
                incoming = next(_incoming(node))
                outgoing = next(_outgoing(node))
                side = (default if not _boolean(incoming, 'REVERSED')
                        or not _boolean(outgoing, 'REVERSED') else _opposite(default))
                apply_dummy_side(node, side)
            for edge in _outgoing(node):
                apply_label_side(edge.labels, _opposite(default) if _boolean(edge, 'REVERSED') else default)


def _regular_port_labels(queue, side, default):
    if len(queue) == 2:
        first, second = ('ABOVE', 'BELOW') if side in ('NORTH', 'EAST') else ('BELOW', 'ABOVE')
        apply_label_side(queue.pop(0), first)
        apply_label_side(queue.pop(0), second)
    else:
        for labels in queue:
            apply_label_side(labels, default)


def _regular_node(node, default):
    queue = []
    current_side = None
    for port in node.ports:
        if port.side != current_side:
            if queue:
                _regular_port_labels(queue, current_side, default)
            queue.clear()
            current_side = port.side
        labels = gather_labels(port)
        if labels is not None:
            queue.append(labels)
    if queue:
        _regular_port_labels(queue, current_side, default)


def _consecutive_run(queue, label_count, top, bottom, default):
    if top and (not bottom or len(queue) > 1) and label_count == 1 and queue[0].type == 'LABEL':
        apply_dummy_side(queue[0], 'ABOVE')
    elif bottom and (not top or len(queue) > 1) and label_count == 1 and queue[-1].type == 'LABEL':
        apply_dummy_side(queue[-1], 'BELOW')
    elif len(queue) == 2:
        apply_dummy_side(queue.pop(0), 'ABOVE')
        apply_dummy_side(queue.pop(0), 'BELOW')
    else:
        _simple_loop_runs(queue, default)
    queue.clear()


def _smart(graph, default):
    queue = []
    for layer in graph.layers:
        top = True
        label_count = 0
        for node in layer.nodes:
            if node.type in ('LABEL', 'LONG_EDGE'):
                if node.type == 'LABEL':
                    label_count += 1
                queue.append(node)
            else:
                if node.type == 'NORMAL':
                    _regular_node(node, default)
                if queue:
                    _consecutive_run(queue, label_count, top, False, default)
                top = False
                label_count = 0
        if queue:
            _consecutive_run(queue, label_count, top, True, default)


def label_side_selector(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    mode = read_layered_scalar(graph, 'EDGE_LABELS_SIDE_SELECTION', 'EDGE_LABELS_SIDE_SELECTION_0')
    monitor.begin('Label side selection (' + str(mode) + ')', 1)
    if mode == 'ALWAYS_UP':
        _same_side(graph, 'ABOVE')
    elif mode == 'ALWAYS_DOWN':
        _same_side(graph, 'BELOW')
    elif mode == 'DIRECTION_UP':
        _based_on_direction(graph, 'ABOVE')
    elif mode == 'DIRECTION_DOWN':
        _based_on_direction(graph, 'BELOW')
    elif mode == 'SMART_UP':
        _smart(graph, 'ABOVE')
    elif mode == 'SMART_DOWN':
        _smart(graph, 'BELOW')
    monitor.done()
