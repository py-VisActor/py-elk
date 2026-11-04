# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P16D in references/e13-kernel-sources.json.
# Native callback/container views; actual selected bodies have separate source approvals.
"""Actual dynamic processor selection and persistent phase assembly.

The factory registry supplies real source factories. This controller does not
substitute missing processor mathematics with empty callbacks.
"""
from ..random import _unseeded_random
from .algorithm_assembler import AlgorithmAssembler
from .graph_info import get_graph_properties
from .layout_configuration import LayeredPhase, LayoutProcessorConfiguration, create_from
from .phases import JavaRandom
from .property_access import read_layered_scalar
from .spacings import Spacings


P1, P2, P3, P4, P5 = tuple(LayeredPhase)


def _read(holder, symbol):
    native_key = 'ASPECT_RATIO' if symbol == 'ASPECT_RATIO_1' else symbol[:-2] if symbol.endswith('_0') else symbol
    return read_layered_scalar(holder, native_key, symbol)


def _graph_of(node):
    return node.graph if node.graph is not None else node.layer.graph


def get_node_flexibility(node):
    key = 'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY'
    if key in node.properties:
        return _read(node, key + '_0')
    return _read(_graph_of(node), key + '_DEFAULT_0')


def get_direction(graph):
    direction = _read(graph, 'DIRECTION')
    if direction == 'UNDEFINED':
        return 'RIGHT' if _read(graph, 'ASPECT_RATIO_1') >= 1 else 'DOWN'
    return direction


def activate_greedy_switch_for(graph):
    if _read(graph, 'HIERARCHY_HANDLING') == 'INCLUDE_CHILDREN':
        return (getattr(graph, 'parent_node', None) is None
                and _read(graph, 'CROSSING_MINIMIZATION_GREEDY_SWITCH_HIERARCHICAL_TYPE_0') != 'OFF')
    switch_type = _read(graph, 'CROSSING_MINIMIZATION_GREEDY_SWITCH_TYPE_0')
    interactive = (_read(graph, 'CROSSING_MINIMIZATION_SEMI_INTERACTIVE_0')
                   or _read(graph, 'CROSSING_MINIMIZATION_STRATEGY_0') == 'INTERACTIVE')
    threshold = _read(graph, 'CROSSING_MINIMIZATION_GREEDY_SWITCH_ACTIVATION_THRESHOLD_0')
    size = len(graph.layerless_nodes)
    return not interactive and switch_type != 'OFF' and (threshold == 0 or threshold > size)


class GraphConfigurator:
    def __init__(self, factories):
        self.factories = factories
        self.algorithm_assembler = AlgorithmAssembler()
        self.baseline = LayoutProcessorConfiguration()
        self.baseline.add_before(P4, self._factory('INNERMOST_NODE_MARGIN_CALCULATOR'))
        self.baseline.add_before(P4, self._factory('LABEL_AND_NODE_SIZE_PROCESSOR'))
        self.baseline.add_before(P5, self._factory('LAYER_SIZE_AND_GRAPH_HEIGHT_CALCULATOR'))
        self.baseline.add_after(P5, self._factory('END_LABEL_SORTER'))
        self.label_management = LayoutProcessorConfiguration()
        self.label_management.add_before(P4, self._factory('CENTER_LABEL_MANAGEMENT_PROCESSOR'))
        self.label_management.add_before(P4, self._factory('END_NODE_PORT_LABEL_MANAGEMENT_PROCESSOR'))
        self.hierarchical = LayoutProcessorConfiguration()
        self.hierarchical.add_after(P5, self._factory('HIERARCHICAL_NODE_RESIZER'))

    def _factory(self, name):
        return self.factories.intermediate(name)

    def _before(self, configuration, phase, name):
        configuration.add_before(phase, self._factory(name))

    def _after(self, configuration, phase, name):
        configuration.add_after(phase, self._factory(name))

    def phase_independent_configuration(self, graph):
        graph_properties = get_graph_properties(graph)
        configuration = create_from(self.baseline)
        hierarchy = _read(graph, 'HIERARCHY_HANDLING')
        if hierarchy == 'INCLUDE_CHILDREN':
            configuration.add_all(self.hierarchical)
        self._before(configuration, P1 if _read(graph, 'FEEDBACK_EDGES_0') else P3, 'PORT_SIDE_PROCESSOR')
        if graph.properties.get('org.eclipse.elk.labels.labelManager') is not None:
            configuration.add_all(self.label_management)
        if _read(graph, 'INTERACTIVE_LAYOUT') or _read(graph, 'GENERATE_POSITION_AND_LAYER_IDS_0'):
            self._after(configuration, P5, 'CONSTRAINTS_POSTPROCESSOR')
        if _read(graph, 'DIRECTION') in ('LEFT', 'DOWN', 'UP'):
            self._before(configuration, P1, 'DIRECTION_PREPROCESSOR')
            self._after(configuration, P5, 'DIRECTION_POSTPROCESSOR')
        if 'COMMENTS' in graph_properties:
            self._before(configuration, P1, 'COMMENT_PREPROCESSOR')
            self._before(configuration, P4, 'COMMENT_NODE_MARGIN_CALCULATOR')
            self._after(configuration, P5, 'COMMENT_POSTPROCESSOR')
        if _read(graph, 'LAYERING_NODE_PROMOTION_STRATEGY_0') != 'NONE':
            self._before(configuration, P3, 'NODE_PROMOTION')
        if 'PARTITIONS' in graph_properties:
            self._before(configuration, P1, 'PARTITION_PREPROCESSOR')
            self._before(configuration, P2, 'PARTITION_MIDPROCESSOR')
            self._before(configuration, P3, 'PARTITION_POSTPROCESSOR')
        if (_read(graph, 'COMPACTION_POST_COMPACTION_STRATEGY_0') != 'NONE'
                and _read(graph, 'EDGE_ROUTING') != 'POLYLINE'):
            self._after(configuration, P5, 'HORIZONTAL_COMPACTOR')
        if _read(graph, 'HIGH_DEGREE_NODES_TREATMENT_0'):
            self._before(configuration, P3, 'HIGH_DEGREE_NODE_LAYER_PROCESSOR')
        if _read(graph, 'CROSSING_MINIMIZATION_SEMI_INTERACTIVE_0'):
            self._before(configuration, P3, 'SEMI_INTERACTIVE_CROSSMIN_PROCESSOR')
        if activate_greedy_switch_for(graph):
            symbol = ('CROSSING_MINIMIZATION_GREEDY_SWITCH_HIERARCHICAL_TYPE_0'
                      if _read(graph, 'HIERARCHY_HANDLING') == 'INCLUDE_CHILDREN'
                      else 'CROSSING_MINIMIZATION_GREEDY_SWITCH_TYPE_0')
            name = 'ONE_SIDED_GREEDY_SWITCH' if _read(graph, symbol) == 'ONE_SIDED' else 'TWO_SIDED_GREEDY_SWITCH'
            self._before(configuration, P4, name)
        if _read(graph, 'LAYER_UNZIPPING_STRATEGY_0') == 'ALTERNATING':
            self._before(configuration, P4, 'ALTERNATING_LAYER_UNZIPPER')
        wrapping = _read(graph, 'WRAPPING_STRATEGY_0')
        if wrapping == 'SINGLE_EDGE':
            self._before(configuration, P4, 'SINGLE_EDGE_GRAPH_WRAPPER')
        elif wrapping == 'MULTI_EDGE':
            self._before(configuration, P3, 'BREAKING_POINT_INSERTER')
            self._before(configuration, P4, 'BREAKING_POINT_PROCESSOR')
            self._after(configuration, P5, 'BREAKING_POINT_REMOVER')
        if _read(graph, 'CONSIDER_MODEL_ORDER_STRATEGY_0') != 'NONE':
            self._before(configuration, P3, 'SORT_BY_INPUT_ORDER_OF_MODEL')
        has_flexibility = any(get_node_flexibility(node) is not None for node in graph.layerless_nodes)
        if has_flexibility and 'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY_RECOMPUTE_NODE_PLACEMENT' in graph.properties:
            self._after(configuration, P4, 'NODE_PLACEMENT_REPEATER')
        return configuration

    def copy_port_constraints(self, node):
        # Iterator frames preserve recursive source order without a host depth cap.
        stack = [iter((node,))]
        while stack:
            try:
                current = next(stack[-1])
            except StopIteration:
                stack.pop()
                continue
            current.properties['ORIGINAL_PORT_CONSTRAINTS'] = _read(current, 'PORT_CONSTRAINTS_0')
            nested = getattr(current, 'nested_graph', None)
            if nested is not None:
                def children(graph):
                    yield from graph.layerless_nodes
                    for layer in graph.layers:
                        yield from layer.nodes
                stack.append(iter(children(nested)))

    def prepare_graph_for_layout(self, graph):
        edge_spacing = _read(graph, 'SPACING_EDGE_EDGE')
        if edge_spacing < 2:
            graph.properties['SPACING_EDGE_EDGE'] = 2.0
        if _read(graph, 'DIRECTION') == 'UNDEFINED':
            graph.properties['DIRECTION'] = get_direction(graph)
        seed = _read(graph, 'RANDOM_SEED_0')
        random = _unseeded_random() if seed == 0 else JavaRandom(seed)
        graph.properties['RANDOM'] = random
        graph.random = random
        if _read(graph, 'NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES_0') is None:
            graph.properties['NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES'] = _read(graph, 'EDGE_ROUTING') == 'ORTHOGONAL'
        for node in graph.layerless_nodes:
            self.copy_port_constraints(node)
        for layer in graph.layers:
            for node in layer.nodes:
                self.copy_port_constraints(node)
        graph.properties['SPACINGS'] = Spacings(graph)
        assembler = self.algorithm_assembler
        assembler.reset()
        for phase, symbol in (
            (P1, 'CYCLE_BREAKING_STRATEGY_0'),
            (P2, 'LAYERING_STRATEGY_0'),
            (P3, 'CROSSING_MINIMIZATION_STRATEGY_0'),
            (P4, 'NODE_PLACEMENT_STRATEGY_0'),
        ):
            assembler.set_phase(phase, self.factories.phase(phase, _read(graph, symbol)))
        assembler.set_phase(P5, self.factories.edge_routing(_read(graph, 'EDGE_ROUTING')))
        assembler.add_processor_configuration(self.phase_independent_configuration(graph))
        graph.properties['PROCESSORS'] = assembler.build(graph)
