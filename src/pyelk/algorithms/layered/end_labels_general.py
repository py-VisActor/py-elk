# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright (c) Kiel University and others.
# Calls the separately attributed Google source sort in ports.py unchanged.
# Fixed elkjs0.12.1 worker275e6caf; P18E EndLabelSorter source closure.
"""Actual end-label grouping and order over live native port label cells."""
from dataclasses import dataclass, field

from ...execution.diagnostics import BasicProgressMonitor
from ..disco import _IdentityMap
from .ports import _source_sort
from .property_access import read_layered_scalar


@dataclass(eq=False)
class LabelGroup:
    edge: object
    labels: list = field(default_factory=list)


def initialize(graph):
    next_id = 0
    for layer in graph.layers:
        for node in layer.nodes:
            node.id = next_id
            next_id += 1
            for port in node.ports:
                port.id = next_id
                next_id += 1


def needs_sorting(port):
    count = 0
    for edge in port.incoming_edges:
        if any(read_layered_scalar(label, 'EDGE_LABELS_PLACEMENT', 'EDGE_LABELS_PLACEMENT') == 'HEAD'
               for label in edge.labels):
            count += 1
    for edge in port.outgoing_edges:
        if any(read_layered_scalar(label, 'EDGE_LABELS_PLACEMENT', 'EDGE_LABELS_PLACEMENT') == 'TAIL'
               for label in edge.labels):
            count += 1
    return count >= 2


def create_label_groups(cell, graph):
    groups = _IdentityMap(graph)
    for label in cell.labels:
        edge = label.get_property('END_LABEL_EDGE')
        if groups.get(edge) is None:
            # The source constructor's addAll(empty, itself) adds no labels.
            groups.put(edge, LabelGroup(edge))
        groups.get(edge).labels.append(label)
    return [group for _, group in groups.items()]


def _compare_number(first, second):
    return -1 if first < second else 1 if first > second else 0


def compare_groups(first, second):
    difference = _compare_number(first.edge.source.id, second.edge.source.id)
    if difference != 0:
        return difference
    difference = _compare_number(first.edge.target.owner.id, second.edge.target.owner.id)
    if difference != 0:
        return difference
    return _compare_number(second.edge.target.id, first.edge.target.id)


def sort_cell(cell, graph):
    groups = create_label_groups(cell, graph)
    _source_sort(groups, compare_groups)
    labels = cell.labels
    labels.clear()
    for group in groups:
        labels.extend(group.labels)


def process_node(node):
    initialized = False
    if 'END_LABELS' in node.properties:
        cells = node.properties['END_LABELS']
        for port in node.ports:
            if needs_sorting(port):
                if not initialized:
                    initialize(node.graph)
                    initialized = True
                sort_cell(cells.get(port), node.graph)


def end_label_sorter(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Sort end labels', 1)
    for layer in graph.layers:
        for node in layer.nodes:
            if node.type == 'NORMAL':
                process_node(node)
    monitor.done()
