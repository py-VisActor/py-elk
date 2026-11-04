# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Components P11C/P11D in references/e13-kernel-sources.json.
# Native continuation/independent-snapshot views; no runtime collections copied.
# Real optimizer loops; pending cost/other strategy dependencies do not fake zero.
"""Actual sweep controller; strategy/cost dependencies are explicit consumers."""
"""Actual sweep controller; strategy/cost dependencies are explicit consumers."""
'Actual sweep controller; strategy/cost dependencies are explicit consumers.'
from .graph_info import GraphInfoHolder
from .integer_box_tokens import holder_integer_box_identity
from .sweep_copy import SweepCopy
from .crossing_counter import _side_view

class IllegalStateException(RuntimeError):
    pass

def _side_ports(node, side):
    ports = _side_view(node, side)
    return list(reversed(ports)) if side in ('WEST', 'SOUTH') else ports

def _first(forward, length):
    return 0 if forward else length - 1

def _end(forward, length):
    return length - 1 if forward else 0

def _array_item(array, index):
    if index < 0 or index >= len(array):
        raise IndexError(index)
    return array[index]

class LayerSweepCrossingMinimizer:

    def __init__(self, cross_min_type, *, box_identity_getter=holder_integer_box_identity):
        self.cross_min_type = cross_min_type
        self.random_seed = 0
        self.box_identity_getter = box_identity_getter

    def initialize(self, root_graph):
        self.graph_info_holders = []
        self.random = root_graph.random
        self.random_seed = self.random.next_long()
        to_sweep = []
        graphs = [root_graph]
        index = 0
        while index < len(graphs):
            graph = graphs[index]
            graph.id = index
            index += 1
            data = GraphInfoHolder(graph, self.cross_min_type, self.graph_info_holders, box_identity_getter=self.box_identity_getter)
            graphs.extend(data.child_graphs)
            self.graph_info_holders.append(data)
            if data.use_bottom_up:
                to_sweep.insert(0, data)
        self.graphs_whose_node_order_changed = {}
        return to_sweep

    def set_currently_best_node_orders(self):
        for graph in self.graphs_whose_node_order_changed:
            graph.set_currently_best_node_and_port_order(SweepCopy(graph.current_node_order))

    def save_all_node_orders_of_changed_graphs(self):
        for graph in self.graphs_whose_node_order_changed:
            graph.set_best_node_and_port_order(SweepCopy(graph.currently_best_node_and_port_order))

    @staticmethod
    def sort_port_dummies_by_port_positions(parent, close_layer, side):
        result = [None] * len(close_layer)
        index = 0
        for port in _side_ports(parent, side):
            if port.properties.get('INSIDE_CONNECTIONS', False):
                dummy = port.properties.get('PORT_DUMMY')
                if index < len(result):
                    result[index] = dummy
                else:
                    result.append(dummy)
                index += 1
        if index < len(close_layer):
            raise IllegalStateException('Expected ' + str(len(close_layer)) + ' hierarchical ports, but found only ' + str(index) + '.')
        return result

    @staticmethod
    def sort_ports_by_dummy_positions_in_last_layer(order, parent, on_right_most_layer):
        last_layer = order[_end(on_right_most_layer, len(order))]
        index = _first(on_right_most_layer, len(last_layer))
        if _array_item(last_layer, index).type != 'EXTERNAL_PORT':
            return
        side = 'EAST' if on_right_most_layer else 'WEST'
        for port_index in range(len(parent.ports)):
            port = parent.ports[port_index]
            if port.side == side and port.properties.get('INSIDE_CONNECTIONS', False):
                parent.ports[port_index] = _array_item(last_layer, index).properties.get('ORIGIN')
                index += 1 if on_right_most_layer else -1

    def set_port_order_on_parent_graph(self, data):
        if not data.has_external_ports:
            return
        snapshot = getattr(data, 'currently_best_node_and_port_order', None) if data.cross_minimizer.is_deterministic() else getattr(data, 'best_node_and_port_order', None)
        if snapshot is not None:
            self.sort_ports_by_dummy_positions_in_last_layer(snapshot.node_order, data.parent, True)
            self.sort_ports_by_dummy_positions_in_last_layer(snapshot.node_order, data.parent, False)
            data.parent.properties['PORT_CONSTRAINTS'] = 'FIXED_ORDER'

    def _hierarchy_steps(self, layer, forward, first_sweep):
        improved = False
        for index in range(len(layer)):
            node = layer[index]
            nested_graph = getattr(node, 'nested_graph', None)
            if nested_graph is None:
                continue
            nested = self.graph_info_holders[nested_graph.id]
            if nested.use_bottom_up:
                continue
            order = nested.current_node_order
            start = _first(forward, len(order))
            if order[start][0].type == 'EXTERNAL_PORT':
                order[start] = self.sort_port_dummies_by_port_positions(node, order[start], 'WEST' if forward else 'EAST')
            else:
                nested.cross_minimizer.set_first_layer_order(order, forward)
            inner_improved = (yield (nested, forward, first_sweep))
            self.sort_ports_by_dummy_positions_in_last_layer(nested.current_node_order, nested.parent, forward)
            improved = int(improved) | int(inner_improved)
        return improved

    def _sweep_steps(self, graph, forward, first_sweep):
        order = graph.current_node_order
        length = len(order)
        start = _first(forward, length)
        improved = graph.port_distributor.distribute_ports_while_sweeping(order, start, forward)
        hierarchical = (yield from self._hierarchy_steps(order[start], forward, first_sweep))
        improved = int(improved) | int(hierarchical)
        indices = range(1, length) if forward else range(length - 2, -1, -1)
        for index in indices:
            first = first_sweep and (not graph.l_graph.properties.get('FIRST_TRY_WITH_INITIAL_ORDER', False)) and (not graph.l_graph.properties.get('SECOND_TRY_WITH_INITIAL_ORDER', False))
            improved = int(improved) | int(graph.cross_minimizer.minimize_crossings(order, index, forward, first))
            improved = int(improved) | int(graph.port_distributor.distribute_ports_while_sweeping(order, index, forward))
            hierarchical = (yield from self._hierarchy_steps(order[index], forward, first_sweep))
            improved = int(improved) | int(hierarchical)
        self.graphs_whose_node_order_changed[graph] = None
        return improved

    def sweep_reducing_crossings(self, graph, forward, first_sweep):
        stack = [self._sweep_steps(graph, forward, first_sweep)]
        sent = None
        while stack:
            try:
                dependency = stack[-1].send(sent)
                sent = None
                stack.append(self._sweep_steps(*dependency))
            except StopIteration as done:
                stack.pop()
                sent = done.value
        return sent

    def transfer_node_and_port_orders_to_graph(self):
        for graph in self.graph_info_holders:
            snapshot = getattr(graph, 'currently_best_node_and_port_order', None) if graph.cross_minimizer.is_deterministic() else getattr(graph, 'best_node_and_port_order', None)
            if snapshot is not None:
                snapshot.transfer_node_and_port_orders_to_graph(graph.l_graph)

    def process(self, graph, monitor):
        monitor.begin('Minimize Crossings ' + self.cross_min_type, 1)
        empty = len(graph.layers) == 0 or not any((layer.nodes for layer in graph.layers))
        single = len(graph.layers) == 1 and len(graph.layers[0].nodes) == 1
        hierarchical = graph.properties.get('HIERARCHY_HANDLING', 'INHERIT') == 'INCLUDE_CHILDREN'
        if empty or (single and (not hierarchical)):
            monitor.done()
            return
        to_sweep = self.initialize(graph)
        first = to_sweep[0]
        if first.cross_minimizer.is_deterministic():
            method = self.minimize_crossings_no_counter if first.cross_minimizer.always_improves() else self.minimize_crossings_with_counter
        else:
            method = self.compare_different_randomized_layouts
        for data in to_sweep:
            if len(data.current_node_order) > 0:
                method(data)
                if data.has_parent:
                    self.set_port_order_on_parent_graph(data)
        self.transfer_node_and_port_orders_to_graph()
        monitor.done()

    def count_current_number_of_crossings(self, graph, weighted=False):
        stack = [[graph, weighted, None, None]]
        while stack:
            frame = stack[-1]
            data, use_weighted = (frame[0], frame[1])
            if frame[2] is None:
                if use_weighted:
                    influence = 0.0
                    props = data.l_graph.properties
                    strategy = props.get('CONSIDER_MODEL_ORDER_STRATEGY', 'NONE')
                    props.get('CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY', 'ONLY_WITHIN_GROUP')
                    node_influence = props.get('CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE', 0.0)
                    port_influence = props.get('CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE', 0.0)
                    if strategy != 'NONE':
                        from .model_order_cost import count_model_order_node_changes, count_model_order_port_changes
                        influence += node_influence * count_model_order_node_changes(data.l_graph, data.current_node_order, strategy)
                        influence += port_influence * count_model_order_port_changes(data.l_graph, data.current_node_order)
                    score = data.crossings_counter.count_all_crossings(data.current_node_order) + influence
                else:
                    score = data.crossings_counter.count_all_crossings(data.current_node_order)
                frame[2] = 0.0 + score
                frame[3] = iter(data.child_graphs)
            for child_graph in frame[3]:
                child = self.graph_info_holders[child_graph.id]
                if not child.use_bottom_up:
                    stack.append([child, False, None, None])
                    break
            else:
                subtotal = frame[2]
                stack.pop()
                if stack:
                    stack[-1][2] += subtotal
                else:
                    return subtotal

    def minimize_crossings_no_counter(self, graph):
        forward = self.random.next(1) != 0
        improved = True
        while improved:
            improved = graph.cross_minimizer.set_first_layer_order(graph.current_node_order, forward)
            improved = int(improved) | int(self.sweep_reducing_crossings(graph, forward, False))
            forward = not forward
        self.set_currently_best_node_orders()

    def _minimize_counted(self, graph, weighted):
        forward = self.random.next(1) != 0
        initial = self.count_current_number_of_crossings(graph, weighted)
        props = graph.l_graph.properties
        if initial == 0 and props.get('FIRST_TRY_WITH_INITIAL_ORDER', False):
            return 0
        if not props.get('FIRST_TRY_WITH_INITIAL_ORDER', False) and (not props.get('SECOND_TRY_WITH_INITIAL_ORDER', False)) or props.get('CONSIDER_MODEL_ORDER_STRATEGY', 'NONE') == 'NONE':
            graph.cross_minimizer.set_first_layer_order(graph.current_node_order, forward)
        else:
            forward = props.get('FIRST_TRY_WITH_INITIAL_ORDER', False)
        self.sweep_reducing_crossings(graph, forward, True)
        if props.get('SECOND_TRY_WITH_INITIAL_ORDER', False):
            props['SECOND_TRY_WITH_INITIAL_ORDER'] = False
        if props.get('FIRST_TRY_WITH_INITIAL_ORDER', False):
            props['FIRST_TRY_WITH_INITIAL_ORDER'] = False
            props['SECOND_TRY_WITH_INITIAL_ORDER'] = True
        crossings = self.count_current_number_of_crossings(graph, weighted)
        while True:
            self.set_currently_best_node_orders()
            if crossings == 0:
                return 0
            forward = not forward
            old = crossings
            self.sweep_reducing_crossings(graph, forward, False)
            crossings = self.count_current_number_of_crossings(graph, weighted)
            if not old > crossings:
                return old

    def minimize_crossings_with_counter(self, graph):
        return self._minimize_counted(graph, False)

    def minimize_crossings_node_port_order_with_counter(self, graph):
        return self._minimize_counted(graph, True)

    def compare_different_randomized_layouts(self, graph):
        self.random.set_seed(self.random_seed)
        self.graphs_whose_node_order_changed.clear()
        props = graph.l_graph.properties
        weighted = props.get('CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE', 0.0) != 0 or props.get('CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE', 0.0) != 0
        best = 1.7976931348623157e+308 if weighted else 2147483647
        if props.get('CONSIDER_MODEL_ORDER_STRATEGY', 'NONE') != 'NONE':
            props['FIRST_TRY_WITH_INITIAL_ORDER'] = True
        thoroughness = props.get('THOROUGHNESS', 7)
        for index in range(thoroughness):
            crossings = self._minimize_counted(graph, weighted)
            if crossings < best:
                best = crossings
                self.save_all_node_orders_of_changed_graphs()
                if best == 0:
                    break
