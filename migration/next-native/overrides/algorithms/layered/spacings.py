# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P16C in references/e13-kernel-sources.json.
# Native descriptors/matrices are original host views; no collection runtime copied.
"""Actual type-pair spacing properties and individual-node scalar reads."""
from collections.abc import Mapping
from dataclasses import dataclass

from ...options.owners import scalar_owner_default
from .port_distribution import _maximum
from .property_access import read_layered_scalar


NODE_TYPES = ('NORMAL', 'LONG_EDGE', 'EXTERNAL_PORT', 'NORTH_SOUTH_PORT',
              'LABEL', 'BREAKING_POINT', 'PLACEHOLDER', 'NONSHIFTING_PLACEHOLDER')


@dataclass(frozen=True)
class SpacingProperty:
    native_key: str
    symbol: str
    canonical_id: str


def _property(symbol):
    canonical, _ = scalar_owner_default('LayeredOptions', symbol)
    native_key = symbol[:-2] if symbol.endswith('_0') else symbol
    return SpacingProperty(native_key, symbol, canonical)


_PROPERTIES = {symbol: _property(symbol) for symbol in (
    'SPACING_NODE_NODE_0', 'SPACING_NODE_NODE_BETWEEN_LAYERS_0',
    'SPACING_EDGE_NODE', 'SPACING_EDGE_NODE_BETWEEN_LAYERS_0',
    'SPACING_EDGE_EDGE', 'SPACING_EDGE_EDGE_BETWEEN_LAYERS_0',
    'SPACING_LABEL_NODE', 'SPACING_PORT_PORT',
    'SPACING_LABEL_PORT_VERTICAL', 'SPACING_LABEL_PORT_HORIZONTAL')}


def _ordinal(node_type):
    if isinstance(node_type, str):
        return NODE_TYPES.index(node_type)
    return node_type.ordinal


def _double(value):
    if type(value) not in (int, float):
        raise TypeError('An actual nonnull Double spacing is required')
    return float(value)


def _graph(node):
    graph = node.graph
    return graph if graph is not None else node.layer.graph


def _read_graph(graph, selected):
    if selected is None:
        raise TypeError('The selected node-type spacing Property is null')
    return read_layered_scalar(graph, selected.native_key, selected.symbol)


def get_individual_or_default(node, selected):
    result = None
    if 'SPACING_INDIVIDUAL' in node.properties:
        individual = node.properties['SPACING_INDIVIDUAL']
        if not isinstance(individual, Mapping):
            raise TypeError('An actual individual spacing PropertyHolder mapping is required')
        if selected is None:
            raise TypeError('The selected node-type spacing Property is null')
        if selected.canonical_id in individual:
            result = individual[selected.canonical_id]
    if result is None:
        result = _read_graph(_graph(node), selected)
    return result


class Spacings:
    def __init__(self, graph):
        self.graph = graph
        count = len(NODE_TYPES)
        self.node_type_spacing_options_horizontal = [[None for _ in range(count)] for _ in range(count)]
        self.node_type_spacing_options_vertical = [[None for _ in range(count)] for _ in range(count)]
        p = _PROPERTIES
        self._diagonal('NORMAL', p['SPACING_NODE_NODE_0'], p['SPACING_NODE_NODE_BETWEEN_LAYERS_0'])
        self._pair('NORMAL', 'LONG_EDGE', p['SPACING_EDGE_NODE'], p['SPACING_EDGE_NODE_BETWEEN_LAYERS_0'])
        self._pair('NORMAL', 'NORTH_SOUTH_PORT', p['SPACING_EDGE_NODE'])
        self._pair('NORMAL', 'EXTERNAL_PORT', p['SPACING_EDGE_NODE'])
        self._pair('NORMAL', 'LABEL', p['SPACING_NODE_NODE_0'], p['SPACING_NODE_NODE_BETWEEN_LAYERS_0'])
        self._diagonal('LONG_EDGE', p['SPACING_EDGE_EDGE'], p['SPACING_EDGE_EDGE_BETWEEN_LAYERS_0'])
        self._pair('LONG_EDGE', 'NORTH_SOUTH_PORT', p['SPACING_EDGE_EDGE'])
        self._pair('LONG_EDGE', 'EXTERNAL_PORT', p['SPACING_EDGE_EDGE'])
        self._pair('LONG_EDGE', 'LABEL', p['SPACING_EDGE_NODE'], p['SPACING_EDGE_NODE_BETWEEN_LAYERS_0'])
        self._diagonal('NORTH_SOUTH_PORT', p['SPACING_EDGE_EDGE'])
        self._pair('NORTH_SOUTH_PORT', 'EXTERNAL_PORT', p['SPACING_EDGE_EDGE'])
        self._pair('NORTH_SOUTH_PORT', 'LABEL', p['SPACING_LABEL_NODE'])
        self._diagonal('EXTERNAL_PORT', p['SPACING_PORT_PORT'])
        self._pair('EXTERNAL_PORT', 'LABEL', p['SPACING_LABEL_PORT_VERTICAL'], p['SPACING_LABEL_PORT_HORIZONTAL'])
        self._diagonal('LABEL', p['SPACING_EDGE_EDGE'], p['SPACING_EDGE_EDGE'])
        self._diagonal('BREAKING_POINT', p['SPACING_EDGE_EDGE'], p['SPACING_EDGE_EDGE_BETWEEN_LAYERS_0'])
        self._pair('BREAKING_POINT', 'NORMAL', p['SPACING_EDGE_NODE'], p['SPACING_EDGE_NODE_BETWEEN_LAYERS_0'])
        self._pair('BREAKING_POINT', 'LABEL', p['SPACING_EDGE_NODE'], p['SPACING_EDGE_NODE_BETWEEN_LAYERS_0'])
        self._pair('BREAKING_POINT', 'LONG_EDGE', p['SPACING_EDGE_NODE'], p['SPACING_EDGE_NODE_BETWEEN_LAYERS_0'])

    def _pair(self, first, second, vertical, horizontal=None):
        left, right = _ordinal(first), _ordinal(second)
        self.node_type_spacing_options_vertical[left][right] = vertical
        self.node_type_spacing_options_vertical[right][left] = vertical
        if horizontal is not None:
            self.node_type_spacing_options_horizontal[left][right] = horizontal
            self.node_type_spacing_options_horizontal[right][left] = horizontal

    def _diagonal(self, node_type, vertical, horizontal=None):
        index = _ordinal(node_type)
        self.node_type_spacing_options_vertical[index][index] = vertical
        if horizontal is not None:
            self.node_type_spacing_options_horizontal[index][index] = horizontal

    def get_horizontal_spacing(self, first_type, second_type):
        selected = self.node_type_spacing_options_horizontal[_ordinal(first_type)][_ordinal(second_type)]
        return _double(_read_graph(self.graph, selected))

    def get_vertical_spacing(self, first, second):
        if hasattr(first, 'type'):
            return self.get_vertical_spacing_nodes(first, second)
        selected = self.node_type_spacing_options_vertical[_ordinal(first)][_ordinal(second)]
        return _double(_read_graph(self.graph, selected))

    def get_vertical_spacing_nodes(self, first, second):
        selected = self.node_type_spacing_options_vertical[_ordinal(first.type)][_ordinal(second.type)]
        first_value = get_individual_or_default(first, selected)
        second_value = get_individual_or_default(second, selected)
        return _maximum(_double(first_value), _double(second_value))
