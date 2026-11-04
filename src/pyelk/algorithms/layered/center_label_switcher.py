# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; approved P26B actual six-strategy switcher.
"""Stateful center-label chain placement and actual dummy rewiring."""
from ...execution.diagnostics import BasicProgressMonitor
from .cell_layout import _maximum
from .graph import set_layer, set_source, set_target
from .ports import _source_sort, double_compare
from .property_access import read_layered_scalar


STRATEGIES = ('MEDIAN_LAYER', 'TAIL_LAYER', 'HEAD_LAYER',
              'SPACE_EFFICIENT_LAYER', 'WIDEST_LAYER', 'CENTER_LAYER')
WIDTH_STRATEGIES = frozenset(STRATEGIES[3:])
_INCLUDE_LABEL = 'edgelabelcenterednessanalysis.includelabel'


def _first_incoming(node):
    return next(edge for port in node.ports for edge in port.incoming_edges)


def _first_outgoing(node):
    return next(edge for port in node.ports for edge in port.outgoing_edges)


def _reversed_edge(info):
    incoming = _first_incoming(info.label_dummy)
    outgoing = _first_outgoing(info.label_dummy)
    return (bool(incoming.properties.get('REVERSED', False))
            or bool(outgoing.properties.get('REVERSED', False)))


def _normal_width(layer):
    if read_layered_scalar(layer.graph, 'DIRECTION', 'DIRECTION') in ('UP', 'DOWN'):
        return 0.0
    result = 0.0
    for node in layer.nodes:
        if node.type == 'NORMAL':
            result = _maximum(result, node.size.x)
    return result


def swap_nodes(label_dummy, long_dummy):
    first_layer, second_layer = label_dummy.layer, long_dummy.layer
    first_index = next(i for i, node in enumerate(first_layer.nodes) if node is label_dummy)
    second_index = next(i for i, node in enumerate(second_layer.nodes) if node is long_dummy)
    first_input = next(port for port in label_dummy.ports if port.incoming_edges)
    first_output = next(port for port in label_dummy.ports if port.outgoing_edges)
    second_input = next(port for port in long_dummy.ports if port.incoming_edges)
    second_output = next(port for port in long_dummy.ports if port.outgoing_edges)
    incoming_first = list(first_input.incoming_edges)
    outgoing_first = list(first_output.outgoing_edges)
    incoming_second = list(second_input.incoming_edges)
    outgoing_second = list(second_output.outgoing_edges)
    set_layer(label_dummy, second_layer, second_index)
    for edge in incoming_second:
        set_target(edge, first_input)
    for edge in outgoing_second:
        set_source(edge, first_output)
    set_layer(long_dummy, first_layer, first_index)
    for edge in incoming_first:
        set_target(edge, second_input)
    for edge in outgoing_first:
        set_source(edge, second_output)


class LabelDummyInfo:
    def __init__(self, label_dummy, default_strategy):
        self.label_dummy = label_dummy
        self.placement_strategy = default_strategy
        self.left_long_edge_dummies = []
        self.right_long_edge_dummies = []
        source = label_dummy
        while True:
            source = _first_incoming(source).source.owner
            if source.type != 'LONG_EDGE':
                break
            self.left_long_edge_dummies.append(source)
        self.left_long_edge_dummies.reverse()
        target = label_dummy
        while True:
            target = _first_outgoing(target).target.owner
            if target.type != 'LONG_EDGE':
                break
            self.right_long_edge_dummies.append(target)
        self.leftmost_layer_id = (self.left_long_edge_dummies[0].layer.id
                                 if self.left_long_edge_dummies else label_dummy.layer.id)
        self.rightmost_layer_id = (self.right_long_edge_dummies[-1].layer.id
                                  if self.right_long_edge_dummies else label_dummy.layer.id)
        for label in label_dummy.properties.get('REPRESENTED_LABELS'):
            if 'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY' in label.properties:
                self.placement_strategy = read_layered_scalar(
                    label, 'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY',
                    'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY_0')
                break

    def ith_dummy(self, index):
        count = len(self.left_long_edge_dummies)
        if index < count:
            return self.left_long_edge_dummies[index]
        if index == count:
            return self.label_dummy
        return self.right_long_edge_dummies[index - count - 1]


class LabelDummySwitcher:
    source_name = 'LabelDummySwitcher'

    def __init__(self):
        self.layer_widths = None

    def get_layout_processor_configuration(self, graph):
        return None

    def assign_layer(self, info, target):
        if target != info.leftmost_layer_id + len(info.left_long_edge_dummies):
            swap_nodes(info.label_dummy, info.ith_dummy(target - info.leftmost_layer_id))
        index = info.label_dummy.layer.id
        self.layer_widths[index] = _maximum(self.layer_widths[index], info.label_dummy.size.x)
        for label in info.label_dummy.properties.get('REPRESENTED_LABELS'):
            label.properties[_INCLUDE_LABEL] = True

    def assign_to_wider_layer(self, info):
        width = info.label_dummy.size.x
        for layer in info.label_dummy.graph.layers[info.leftmost_layer_id:info.rightmost_layer_id + 1]:
            if layer.size.x >= width:
                self.assign_layer(info, layer.id)
                return True
        return False

    def width_sums(self, info):
        graph = info.label_dummy.graph
        edge_spacing = read_layered_scalar(
            graph, 'SPACING_EDGE_NODE_BETWEEN_LAYERS', 'SPACING_EDGE_NODE_BETWEEN_LAYERS_0') * 2
        node_spacing = read_layered_scalar(
            graph, 'SPACING_NODE_NODE_BETWEEN_LAYERS', 'SPACING_NODE_NODE_BETWEEN_LAYERS_0')
        spacing = _maximum(edge_spacing, node_spacing)
        result = []
        current = -spacing
        for dummy in info.left_long_edge_dummies:
            current += self.layer_widths[dummy.layer.id] + spacing
            result.append(current)
        current += self.layer_widths[info.label_dummy.layer.id] + spacing
        result.append(current)
        for dummy in info.right_long_edge_dummies:
            current += self.layer_widths[dummy.layer.id] + spacing
            result.append(current)
        return result

    def center_layer(self, info):
        sums = self.width_sums(info)
        threshold = sums[-1] / 2
        for index, value in enumerate(sums):
            if value >= threshold:
                return info.leftmost_layer_id + index
        return info.leftmost_layer_id + len(info.left_long_edge_dummies)

    def widest_layer(self, info):
        widest = info.leftmost_layer_id
        for index in range(widest + 1, info.rightmost_layer_id + 1):
            if self.layer_widths[index] > self.layer_widths[widest]:
                widest = index
        return widest

    def potentially_widest_layer(self, infos, label_index):
        info = infos[label_index]
        dummy_width = info.label_dummy.size.x
        widest = info.leftmost_layer_id
        widest_width = 0.0
        for index in range(info.leftmost_layer_id, info.rightmost_layer_id + 1):
            if dummy_width <= self.layer_widths[index]:
                return index
            potential = self.layer_widths[index]
            last_unassigned = None
            for later in infos[label_index + 1:]:
                if later.leftmost_layer_id <= index and later.rightmost_layer_id >= index:
                    last_unassigned = later
            if last_unassigned is not None:
                potential = _maximum(potential, last_unassigned.label_dummy.size.x)
            if potential > widest_width:
                widest, widest_width = index, potential
        return widest

    def space_efficient(self, infos):
        remaining = []
        for info in infos:
            if info.leftmost_layer_id == info.rightmost_layer_id:
                self.assign_layer(info, info.leftmost_layer_id)
            elif not self.assign_to_wider_layer(info):
                remaining.append(info)
        if not remaining:
            return
        _source_sort(remaining, lambda first, second: double_compare(
            second.label_dummy.size.x, first.label_dummy.size.x))
        for index, info in enumerate(remaining):
            self.assign_layer(info, self.potentially_widest_layer(remaining, index))

    def process_strategy(self, infos):
        if not infos:
            return
        if infos[0].placement_strategy == 'SPACE_EFFICIENT_LAYER':
            self.space_efficient(infos)
            return
        for info in infos:
            strategy = info.placement_strategy
            if strategy == 'CENTER_LAYER':
                self.assign_layer(info, self.center_layer(info))
            elif strategy == 'MEDIAN_LAYER':
                layers = info.rightmost_layer_id - info.leftmost_layer_id + 1
                lower_median = int((layers - 1) / 2) & 0xffffffff
                if lower_median >= 0x80000000:
                    lower_median -= 0x100000000
                self.assign_layer(info, info.leftmost_layer_id + lower_median)
            elif strategy == 'WIDEST_LAYER':
                self.assign_layer(info, self.widest_layer(info))
            elif strategy in ('HEAD_LAYER', 'TAIL_LAYER'):
                head = strategy == 'HEAD_LAYER'
                reversed_edge = _reversed_edge(info)
                info.label_dummy.properties['ALIGNMENT'] = (
                    'RIGHT' if (head and not reversed_edge) or (not head and reversed_edge) else 'LEFT')
                reversed_edge = _reversed_edge(info)
                target = (info.leftmost_layer_id if reversed_edge else info.rightmost_layer_id
                          ) if head else (info.rightmost_layer_id if reversed_edge else info.leftmost_layer_id)
                self.assign_layer(info, target)
            node = _first_incoming(info.label_dummy).source.owner
            while node.type == 'LONG_EDGE':
                node.properties['LONG_EDGE_BEFORE_LABEL_DUMMY'] = True
                node = _first_incoming(node).source.owner

    def process(self, graph, monitor=None):
        if monitor is None:
            monitor = BasicProgressMonitor()
        monitor.begin('Label dummy switching', 1)
        default = read_layered_scalar(graph, 'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY',
                                      'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY_0')
        for index, layer in enumerate(graph.layers):
            layer.id = index
        infos = {strategy: [] for strategy in STRATEGIES}
        for layer in graph.layers:
            for node in layer.nodes:
                if node.type == 'LABEL':
                    info = LabelDummyInfo(node, default)
                    infos[info.placement_strategy].append(info)
        self.layer_widths = [0.0] * len(graph.layers)
        for strategy in STRATEGIES:
            if strategy in WIDTH_STRATEGIES and infos[strategy]:
                for layer in graph.layers:
                    self.layer_widths[layer.id] = _normal_width(layer)
                break
        for strategy in STRATEGIES:
            if strategy not in WIDTH_STRATEGIES:
                self.process_strategy(infos[strategy])
        for strategy in STRATEGIES:
            if strategy in WIDTH_STRATEGIES:
                self.process_strategy(infos[strategy])
        self.layer_widths = None
        monitor.done()
