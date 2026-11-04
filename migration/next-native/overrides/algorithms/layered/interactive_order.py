# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs0.12.1 worker275e6caf, 33269-33280, 53223-53384, 54318-54344.
"""Interactive and explicitly disabled crossing minimization."""
from ...execution.diagnostics import BasicProgressMonitor
from ...execution.node_micro import VectorChain
from .graph import Vec2
from .graph_info import get_graph_properties, _DistributorReceiver
from .forster_constraints import _successors
from .port_distribution import NodeRelativePortDistributor
from .all_crossings import initialize_crossing_receivers
from .ports import _source_sort, double_compare, _divide
from .property_access import read_layered_scalar

_INTERACTIVE_CONFIGURATION = None
_NONE_CONFIGURATION = None


def interactive_reference_point(node):
    graph = node.graph if node.graph is not None else node.layer.graph
    choice = read_layered_scalar(graph, 'INTERACTIVE_REFERENCE_POINT', 'INTERACTIVE_REFERENCE_POINT_0')
    if choice == 'CENTER':
        return Vec2(node.pos.x + node.size.x / 2, node.pos.y + node.size.y / 2)
    if choice == 'TOP_LEFT':
        return Vec2(node.pos.x, node.pos.y)
    return None


def _configuration(interactive):
    global _INTERACTIVE_CONFIGURATION, _NONE_CONFIGURATION
    current = _INTERACTIVE_CONFIGURATION if interactive else _NONE_CONFIGURATION
    if current is None:
        from .layout_configuration import LayoutProcessorConfiguration, LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as I
        p = tuple(LayeredPhase)
        current = LayoutProcessorConfiguration()
        current.add_before(p[2], I.LONG_EDGE_SPLITTER)
        current.add_before(p[3], I.IN_LAYER_CONSTRAINT_PROCESSOR)
        current.add_after(p[4], I.LONG_EDGE_JOINER)
        if interactive: _INTERACTIVE_CONFIGURATION = current
        else: _NONE_CONFIGURATION = current
    return current


def get_position(node, horizontal_position):
    if node.type == 'LONG_EDGE':
        edge = node.properties.get('ORIGIN')
        points = edge.properties.get('ORIGINAL_BENDPOINTS')
        if points is None:
            points = VectorChain()
        elif edge.properties.get('REVERSED', False):
            points = VectorChain(Vec2(p.x, p.y) for p in reversed(points))
        source = node.properties.get('LONG_EDGE_SOURCE')
        if source is not None:
            point = Vec2(((0.0 + source.owner.pos.x) + source.pos.x) + source.anchor.x,
                         ((0.0 + source.owner.pos.y) + source.pos.y) + source.anchor.y)
            if horizontal_position <= point.x: return point.y
            points.insert(0, point)
        target = node.properties.get('LONG_EDGE_TARGET')
        if target is not None:
            point = Vec2(((0.0 + target.owner.pos.x) + target.pos.x) + target.anchor.x,
                         ((0.0 + target.owner.pos.y) + target.pos.y) + target.anchor.y)
            if point.x <= horizontal_position: return point.y
            points.append(point)
        if len(points) >= 2:
            first, second = points[0], points[1]
            index = 2
            while second.x < horizontal_position and index < len(points):
                first, second = second, points[index]
                index += 1
            return first.y + _divide(horizontal_position - first.x, second.x - first.x) * (second.y - first.y)
    elif node.type == 'NORTH_SOUTH_PORT':
        original = node.ports[0].properties.get('ORIGIN')
        owner = original.owner
        if original.side == 'NORTH': return owner.pos.y
        if original.side == 'SOUTH': return owner.pos.y + owner.size.y
    return interactive_reference_point(node).y


class InteractiveCrossingMinimizer:
    source_name = 'InteractiveCrossingMinimizer'

    def __init__(self): _configuration(True)

    def get_layout_processor_configuration(self, graph):
        from .layout_configuration import create_from, LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as I
        configuration = create_from(_configuration(True))
        if 'NON_FREE_PORTS' in get_graph_properties(graph):
            configuration.add_before(tuple(LayeredPhase)[2], I.PORT_LIST_SORTER)
        return configuration

    def process(self, graph, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Interactive crossing minimization', 1)
        for index, layer in enumerate(graph.layers): layer.id = index
        order = [list(layer.nodes) for layer in graph.layers]
        distributor = NodeRelativePortDistributor(len(order))
        initialize_crossing_receivers([_DistributorReceiver(distributor)], order)
        port_count = 0
        for index, layer in enumerate(graph.layers):
            horizontal = 0.0; count = 0
            for node in layer.nodes:
                if node.pos.x > 0:
                    horizontal += node.pos.x + node.size.x / 2
                    count += 1
                for port in node.ports:
                    port.id = port_count; port_count += 1
            if count > 0: horizontal /= count
            positions = [0.0] * len(layer.nodes)
            for node_index, node in enumerate(layer.nodes):
                node.id = node_index
                positions[node_index] = get_position(node, horizontal)
                if node.type == 'LONG_EDGE':
                    node.properties['ORIGINAL_DUMMY_NODE_POSITION'] = positions[node_index]
            def compare(first, second):
                result = double_compare(positions[first.id], positions[second.id])
                if result == 0:
                    first_successors = _successors(first)
                    second_successors = _successors(second)
                    if second in first_successors: return -1
                    if first in second_successors: return 1
                return result
            _source_sort(layer.nodes, compare)
            # Source retains the pre-sort node-array snapshot here.
            distributor.distribute_ports_while_sweeping(order, index, True)
        monitor.done()


class NoCrossingMinimizer:
    source_name = 'NoCrossingMinimizer'

    def __init__(self): _configuration(False)

    def get_layout_processor_configuration(self, graph):
        from .layout_configuration import create_from, LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as I
        configuration = create_from(_configuration(False))
        configuration.add_before(tuple(LayeredPhase)[2], I.PORT_LIST_SORTER)
        return configuration

    def process(self, graph, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('No crossing minimization', 1)
        monitor.done()
