# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs0.12.1 worker275e6caf, 55481-55993.
"""Linear-segment dependency sorting, pendulum balancing and final alignment."""
from collections import deque
from dataclasses import dataclass, field
from ...execution.diagnostics import BasicProgressMonitor
from .graph_info import get_graph_properties
from .integer_box_tokens import value_of_integer_box
from .ports import _divide
from .port_distribution import _maximum, _minimum
from .property_access import read_layered_scalar

_MAX_INT = 2147483647
_MIN_INT = -2147483648
_CONFIGURATION = None
_INPUT = 'linearSegments.inputPrio'
_OUTPUT = 'linearSegments.outputPrio'


def _configuration():
    global _CONFIGURATION
    if _CONFIGURATION is None:
        from .layout_configuration import LayoutProcessorConfiguration, LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as I
        _CONFIGURATION = LayoutProcessorConfiguration()
        _CONFIGURATION.add_before(tuple(LayeredPhase)[4], I.HIERARCHICAL_PORT_POSITION_PROCESSOR)
    return _CONFIGURATION


def _integer(node, key, value):
    value = int(value)
    if hasattr(node.properties, 'set_property'):
        node.properties.set_property(key, value, integer_box=value_of_integer_box(value))
    else:
        node.properties[key] = value


@dataclass(eq=False)
class LinearSegment:
    id: int = 0
    nodes: list = field(default_factory=list)
    deflection: float = 0.0
    weight: int = 0
    last_layer: int = -1
    index_in_last_layer: int = -1
    ref_segment: object = None

    def region(self):
        segment = self
        while segment.ref_segment is not None: segment = segment.ref_segment
        return segment

    def split(self, node, new_id):
        index = next(i for i, n in enumerate(self.nodes) if n is node)
        other = LinearSegment(new_id)
        other.nodes.extend(self.nodes[index:])
        del self.nodes[index:]
        for item in other.nodes: item.id = new_id
        return other


class LinearSegmentsNodePlacer:
    source_name = 'LinearSegmentsNodePlacer'

    def __init__(self):
        _configuration()
        self.spacings = None
        self.linear_segments = None

    def get_layout_processor_configuration(self, graph):
        return _configuration() if 'EXTERNAL_PORTS' in get_graph_properties(graph) else None

    def fill_segment(self, node, segment):
        if node.id >= 0: return False
        while True:
            node.id = segment.id
            segment.nodes.append(node)
            following = None
            if node.type in ('LONG_EDGE', 'NORTH_SOUTH_PORT'):
                for port in node.ports:
                    for edge in port.outgoing_edges:
                        target = edge.target.owner
                        if (node.layer is not target.layer and target.type in ('LONG_EDGE', 'NORTH_SOUTH_PORT')
                                and target.id < 0):
                            following = target
                            break
                    if following is not None: break
            if following is None: return True
            node = following

    def create_dependency_graph_edges(self, graph, segments, outgoing, incoming):
        next_id = len(segments)
        layer_index = 0
        for layer in graph.layers:
            if not layer.nodes: continue
            previous = None
            for index, current in enumerate(layer.nodes):
                segment = segments[current.id]
                if segment.index_in_last_layer >= 0:
                    cycle = None
                    for candidate in layer.nodes[index + 1:]:
                        other = segments[candidate.id]
                        if (other.last_layer == segment.last_layer and
                                other.index_in_last_layer < segment.index_in_last_layer):
                            cycle = other
                            break
                    if cycle is not None:
                        if previous is not None:
                            incoming[current.id] -= 1
                            values = outgoing[previous.id]
                            match = next((i for i, v in enumerate(values) if v.id == segment.id), None)
                            if match is not None: values.pop(match)
                        segment = segment.split(current, next_id)
                        next_id += 1; segments.append(segment); outgoing.append([])
                        if previous is not None:
                            outgoing[previous.id].append(segment); incoming.append(1)
                        else: incoming.append(0)
                if index + 1 < len(layer.nodes):
                    following = layer.nodes[index + 1]
                    outgoing[current.id].append(segments[following.id])
                    incoming[following.id] += 1
                segment.last_layer = layer_index
                segment.index_in_last_layer = index
                previous = current
            layer_index += 1

    def sort_linear_segments(self, graph):
        segments = []
        for layer in graph.layers:
            for node in layer.nodes:
                node.id = -1
                input_priority = output_priority = _MIN_INT
                for port in node.ports:
                    for edge in port.incoming_edges:
                        input_priority = _maximum(input_priority, read_layered_scalar(edge, 'PRIORITY_STRAIGHTNESS', 'PRIORITY_STRAIGHTNESS_0'))
                    for edge in port.outgoing_edges:
                        output_priority = _maximum(output_priority, read_layered_scalar(edge, 'PRIORITY_STRAIGHTNESS', 'PRIORITY_STRAIGHTNESS_0'))
                _integer(node, _INPUT, input_priority); _integer(node, _OUTPUT, output_priority)
        for layer in graph.layers:
            for node in layer.nodes:
                if node.id < 0:
                    segment = LinearSegment(len(segments))
                    self.fill_segment(node, segment); segments.append(segment)
        outgoing = [[] for _ in segments]; incoming = [0 for _ in segments]
        self.create_dependency_graph_edges(graph, segments, outgoing, incoming)
        ranks = [0] * len(segments); rank = 0
        ready = deque(segment for segment in segments if incoming[segment.id] == 0)
        while ready:
            segment = ready.popleft(); ranks[segment.id] = rank; rank += 1
            while outgoing[segment.id]:
                target = outgoing[segment.id].pop(0); incoming[target.id] -= 1
                if incoming[target.id] == 0: ready.append(target)
        self.linear_segments = [None] * len(segments)
        for index, segment in enumerate(segments):
            rank = ranks[index]; self.linear_segments[rank] = segment; segment.id = rank
            for node in segment.nodes: node.id = rank
        return self.linear_segments

    def create_unbalanced_placement(self, graph):
        counts = [0] * len(graph.layers); recent = [None] * len(graph.layers)
        for segment in self.linear_segments:
            uppermost = 0.0
            for node in segment.nodes:
                index = next(i for i, layer in enumerate(graph.layers) if node.layer is layer)
                counts[index] += 1
                spacing = read_layered_scalar(graph, 'SPACING_EDGE_EDGE', 'SPACING_EDGE_EDGE')
                if counts[index] > 0 and recent[index] is not None:
                    spacing = self.spacings.get_vertical_spacing_nodes(recent[index], node)
                uppermost = _maximum(uppermost, node.layer.size.y + spacing)
            for node in segment.nodes:
                node.pos.y = uppermost + node.margin.top
                node.layer.size.y = ((uppermost + node.margin.top) + node.size.y) + node.margin.bottom
                index = next(i for i, layer in enumerate(graph.layers) if node.layer is layer)
                recent[index] = node

    def calc_deflection(self, segment, incoming, outgoing, dampening):
        total = 0.0; node_weight = 0
        for node in segment.nodes:
            deflection = 0.0; edge_weight = 0
            input_priority = node.properties.get(_INPUT, 0) if incoming else _MIN_INT
            output_priority = node.properties.get(_OUTPUT, 0) if outgoing else _MIN_INT
            minimum_priority = _maximum(input_priority, output_priority)
            for port in node.ports:
                position = (node.pos.y + port.pos.y) + port.anchor.y
                for enabled, edges, target in ((outgoing, port.outgoing_edges, True), (incoming, port.incoming_edges, False)):
                    if not enabled: continue
                    for edge in edges:
                        other_port = edge.target if target else edge.source
                        other = other_port.owner
                        if segment is not self.linear_segments[other.id]:
                            other_priority = _maximum(other.properties.get(_INPUT, 0), other.properties.get(_OUTPUT, 0))
                            priority = read_layered_scalar(edge, 'PRIORITY_STRAIGHTNESS', 'PRIORITY_STRAIGHTNESS_0')
                            if priority >= minimum_priority and priority >= other_priority:
                                deflection += ((other.pos.y + other_port.pos.y) + other_port.anchor.y) - position
                                edge_weight += 1
            if edge_weight > 0:
                total += deflection / edge_weight; node_weight += 1
        if node_weight > 0:
            segment.deflection = dampening * total / node_weight; segment.weight = node_weight
        else:
            segment.deflection = 0.0; segment.weight = 0

    def merge_regions(self, graph):
        changed = False
        threshold = 1e-4 * read_layered_scalar(graph, 'SPACING_NODE_NODE', 'SPACING_NODE_NODE_0')
        for layer in graph.layers:
            node1 = layer.nodes[0]; region1 = self.linear_segments[node1.id].region()
            for node2 in layer.nodes[1:]:
                region2 = self.linear_segments[node2.id].region()
                if region1 is not region2:
                    spacing = self.spacings.get_vertical_spacing_nodes(node1, node2)
                    first_extent = (((node1.pos.y + node1.size.y) + node1.margin.bottom) + region1.deflection) + spacing
                    second_extent = (node2.pos.y - node2.margin.top) + region2.deflection
                    if first_extent > second_extent + threshold:
                        weight = region1.weight + region2.weight
                        region2.deflection = _divide(region2.weight * region2.deflection + region1.weight * region1.deflection, weight)
                        region2.weight = weight; region1.ref_segment = region2; changed = True
                node1, region1 = node2, region2
        return changed

    def balance_placement(self, graph):
        dampening = read_layered_scalar(graph, 'NODE_PLACEMENT_LINEAR_SEGMENTS_DEFLECTION_DAMPENING', 'NODE_PLACEMENT_LINEAR_SEGMENTS_DEFLECTION_DAMPENING_0')
        thoroughness = read_layered_scalar(graph, 'THOROUGHNESS', 'THOROUGHNESS_0')
        pendulum_iterations = 4; final_iterations = 3; threshold = _divide(20.0, thoroughness)
        ready = False; mode = 0; last_deflection = _MAX_INT
        while True:
            incoming = mode != 1; outgoing = mode != 0; total = 0.0
            for segment in self.linear_segments:
                segment.ref_segment = None
                self.calc_deflection(segment, incoming, outgoing, dampening)
                total += abs(segment.deflection)
            while self.merge_regions(graph): pass
            for segment in self.linear_segments:
                deflection = segment.region().deflection
                if deflection != 0:
                    for node in segment.nodes: node.pos.y += deflection
            if mode in (0, 1):
                pendulum_iterations -= 1
                if pendulum_iterations <= 0 and (total < last_deflection or -pendulum_iterations > thoroughness):
                    mode = 2; last_deflection = _MAX_INT
                elif mode == 0:
                    mode = 1; last_deflection = total
                else:
                    mode = 0; last_deflection = total
            else:
                ready = total >= last_deflection or last_deflection - total < threshold
                last_deflection = total
                if ready: final_iterations -= 1
            if ready and final_iterations <= 0: break

    def post_process(self):
        for segment in self.linear_segments:
            above = below = _MAX_INT
            for node in segment.nodes:
                index = next((i for i, n in enumerate(node.layer.nodes) if n is node), -1) if node.layer is not None else -1
                if index > 0:
                    neighbor = node.layer.nodes[index - 1]
                    spacing = self.spacings.get_vertical_spacing_nodes(node, neighbor)
                    room = (node.pos.y - node.margin.top) - (((neighbor.pos.y + neighbor.size.y) + neighbor.margin.bottom) + spacing)
                else: room = node.pos.y - node.margin.top
                above = _minimum(room, above)
                if index < len(node.layer.nodes) - 1:
                    neighbor = node.layer.nodes[index + 1]
                    spacing = self.spacings.get_vertical_spacing_nodes(node, neighbor)
                    room = (neighbor.pos.y - neighbor.margin.top) - (((node.pos.y + node.size.y) + node.margin.bottom) + spacing)
                else: room = 2 * node.pos.y
                below = _minimum(room, below)
            displacement = _MAX_INT; found = False
            first = segment.nodes[0]; last = segment.nodes[-1]
            for node, incoming in ((first, True), (last, False)):
                for port in node.ports:
                    position = (node.pos.y + port.pos.y) + port.anchor.y
                    for edge in (port.incoming_edges if incoming else port.outgoing_edges):
                        other = edge.source if incoming else edge.target
                        delta = ((other.owner.pos.y + other.pos.y) + other.anchor.y) - position
                        if abs(delta) < abs(displacement) and abs(delta) < (above if delta < 0 else below):
                            displacement = delta; found = True
            if found and displacement != 0:
                for node in segment.nodes: node.pos.y += displacement

    def process(self, graph, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Linear segments node placement', 1)
        self.spacings = graph.properties.get('SPACINGS')
        self.sort_linear_segments(graph)
        self.create_unbalanced_placement(graph)
        self.balance_placement(graph)
        self.post_process()
        self.linear_segments = None; self.spacings = None
        monitor.done()
