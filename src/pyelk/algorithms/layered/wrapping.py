# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# elkjs 0.12.1 worker275e6caf; wrapping/unzipping, lines46738–48059.
"""Layer unzipping and the source wrapping statistics/cut heuristics."""
import math

from ...execution.diagnostics import BasicProgressMonitor
from .graph import LNode, LPort, LEdge, Layer, set_layer, set_port_owner, set_source, set_target
from .native_properties import CanonicalPropertyMap
from .property_access import read_layered_scalar
from .long_edges_general import split_edge, _copy_properties, _floor
from .ports import set_side
from .cell_layout import _maximum
from .port_label_placement import _minimum


def read(holder, key):
    return read_layered_scalar(holder, key, key + '_0')


def incoming(node):
    for port in node.ports:
        yield from port.incoming_edges


def outgoing(node):
    for port in node.ports:
        yield from port.outgoing_edges


def divide(a, b):
    if b == 0:
        return math.nan if a == 0 or math.isnan(a) else math.copysign(math.inf, a * math.copysign(1, b))
    return a / b


def rounded_int(value):
    # Math.round -> GWT long -> int (low 32 bits).
    if math.isnan(value):
        number = 0
    elif value >= 9223372036854775807:
        number = 9223372036854775807
    elif value <= -9223372036854775808:
        number = -9223372036854775808
    else:
        low = math.floor(value)
        number = low + (1 if value - low >= .5 else 0)
    return ((number + 2147483648) % 4294967296) - 2147483648


def new_node(graph, kind):
    node = LNode(graph, type=kind, properties=CanonicalPropertyMap())
    node.integer_box_identities = node.properties.integer_boxes
    return node


def new_port(node, side):
    port = LPort(properties=CanonicalPropertyMap())
    port.integer_box_identities = port.properties.integer_boxes
    set_port_owner(port, node)
    set_side(port, side)
    return port


def new_edge(source=None, target=None):
    edge = LEdge(properties=CanonicalPropertyMap())
    edge.integer_box_identities = edge.properties.integer_boxes
    set_source(edge, source)
    set_target(edge, target)
    return edge


def dummy_node(graph, edge):
    node = new_node(graph, 'LONG_EDGE')
    node.properties['ORIGIN'] = edge
    node.properties['PORT_CONSTRAINTS'] = 'FIXED_POS'
    return node


def _insert(node, layer, index):
    set_layer(node, layer, index if index <= len(layer.nodes) else None)


def _shift_node(graph, sublayers, target, index):
    node = sublayers[0].nodes[index]
    if target > 0:
        set_layer(node, sublayers[target])
    count = 0
    no_incoming = True
    for edge in reversed(list(incoming(node))):
        no_incoming = False
        for layer_index in range(target):
            dummy = dummy_node(graph, edge)
            _insert(dummy, sublayers[layer_index], index + count)
            edge = split_edge(edge, dummy)
        if target > 0:
            count += 1
    if no_incoming:
        for layer_index in range(target):
            _insert(new_node(graph, 'PLACEHOLDER'), sublayers[layer_index], index + count)
        if target > 0:
            count += 1
    extra = False
    for edge in outgoing(node):
        for layer_index in range(target + 1, len(sublayers)):
            dummy = dummy_node(graph, edge)
            set_layer(dummy, sublayers[layer_index])
            edge = split_edge(edge, dummy)
        for layer_index in range(target + 1):
            if extra:
                _insert(new_node(graph, 'NONSHIFTING_PLACEHOLDER'), sublayers[layer_index], index + 1)
        if extra:
            count += 1
        extra = True
    return count - 1 if count > 0 else 0


def alternating_layer_unzipper(graph, *, monitor=None):
    # Source intentionally has no monitor lifecycle for this processor.
    offset = 1
    new_layers = []
    for i, layer in enumerate(graph.layers):
        explicit = [read(node, 'LAYER_UNZIPPING_LAYER_SPLIT') for node in layer.nodes
                    if 'LAYER_UNZIPPING_LAYER_SPLIT' in node.properties]
        n = min(explicit) if explicit else read(graph, 'LAYER_UNZIPPING_LAYER_SPLIT')
        reset = not any(not read(node, 'LAYER_UNZIPPING_RESET_ON_LONG_EDGES') for node in layer.nodes
                        if 'LAYER_UNZIPPING_RESET_ON_LONG_EDGES' in node.properties)
        minimize = any(read(node, 'LAYER_UNZIPPING_MINIMIZE_EDGE_LENGTH') for node in layer.nodes
                       if 'LAYER_UNZIPPING_MINIMIZE_EDGE_LENGTH' in node.properties)
        if minimize:
            width = height = 0.0
            for node in layer.nodes:
                width = _maximum(width, node.size.x)
                height += node.size.y
            height = divide(height, len(layer.nodes))
            width += _maximum(2 * read(graph, 'SPACING_EDGE_NODE_BETWEEN_LAYERS'),
                              _maximum(len(layer.nodes) * read(graph, 'SPACING_EDGE_EDGE_BETWEEN_LAYERS'),
                                       read(graph, 'SPACING_NODE_NODE_BETWEEN_LAYERS')))
            height += _maximum(read(graph, 'SPACING_NODE_NODE'),
                               read_layered_scalar(graph, 'SPACING_EDGE_NODE', 'SPACING_EDGE_NODE'))
            if divide(width, height) >= len(layer.nodes) / 4:
                continue
        if len(layer.nodes) >= n:
            sublayers = [layer]
            for j in range(n - 1):
                new = Layer(graph)
                new_layers.append((new, i + j + offset))
                sublayers.append(new)
            offset += n - 1
            count = len(layer.nodes)
            j = index = target = 0
            while j < count:
                node = layer.nodes[index]
                if node.type != 'NONSHIFTING_PLACEHOLDER':
                    index += _shift_node(graph, sublayers, target % n, index)
                else:
                    j -= 1
                    target -= 1
                if reset and node.type == 'LONG_EDGE':
                    target = -1
                j += 1
                index += 1
                target += 1
    for layer, index in new_layers:
        graph.layers.insert(index, layer)
    for layer in graph.layers:
        layer.nodes[:] = [node for node in layer.nodes
                          if node.type not in ('PLACEHOLDER', 'NONSHIFTING_PLACEHOLDER')]


def insert_dummies(graph, original_edge, offset_first):
    individual = CanonicalPropertyMap()
    individual['SPACING_EDGE_NODE'] = (read_layered_scalar(graph, 'SPACING_EDGE_NODE', 'SPACING_EDGE_NODE')
                                       + read(graph, 'WRAPPING_ADDITIONAL_EDGE_SPACING'))
    edge = original_edge
    target = edge.target
    first = graph.layers.index(edge.source.owner.layer)
    last = graph.layers.index(target.owner.layer)
    created = []
    for i in range(first, last + 1):
        dummy = dummy_node(graph, edge)
        dummy.properties['SPACING_INDIVIDUAL'] = individual
        layer = graph.layers[i]
        set_layer(dummy, layer, len(layer.nodes) - offset_first if i == first else None)
        thickness = read_layered_scalar(edge, 'EDGE_THICKNESS', 'EDGE_THICKNESS_0')
        if thickness < 0:
            thickness = 0.0
            edge.properties['EDGE_THICKNESS'] = thickness
        dummy.size.y = thickness
        p_in, p_out = new_port(dummy, 'WEST'), new_port(dummy, 'EAST')
        p_in.pos.y = p_out.pos.y = _floor(thickness / 2)
        set_target(edge, p_in)
        generated = new_edge()
        _copy_properties(generated, edge)
        generated.properties['JUNCTION_POINTS'] = None
        set_source(generated, p_out)
        set_target(generated, target)
        source_node = edge.source.owner
        if source_node.type == 'LONG_EDGE':
            dummy.properties['LONG_EDGE_SOURCE'] = source_node.properties.get('LONG_EDGE_SOURCE')
            dummy.properties['LONG_EDGE_TARGET'] = source_node.properties.get('LONG_EDGE_TARGET')
        else:
            dummy.properties['LONG_EDGE_SOURCE'] = edge.source
            dummy.properties['LONG_EDGE_TARGET'] = generated.target
        created.append(generated)
        edge = generated
    return created


class GraphStats:
    def __init__(self, graph):
        self.graph = graph
        ar = read_layered_scalar(graph, 'ASPECT_RATIO', 'ASPECT_RATIO_1') * read(graph, 'WRAPPING_CORRECTION_FACTOR')
        self.dar = ar if read_layered_scalar(graph, 'DIRECTION', 'DIRECTION') in ('LEFT', 'RIGHT', 'UNDEFINED') else divide(1, ar)
        self.spacing = read(graph, 'SPACING_NODE_NODE_BETWEEN_LAYERS')
        self.in_layer_spacing = read(graph, 'SPACING_NODE_NODE')
        self.longest_path = len(graph.layers)
        self.widths = self.heights = self.cuts_allowed = None

    def layer_width(self, layer):
        result = 0.0
        for node in layer.nodes:
            result = _maximum(result, node.size.x + node.margin.right + node.margin.left + self.spacing)
        return result

    def layer_height(self, layer):
        result = 0.0
        for node in layer.nodes:
            result += node.size.y + node.margin.bottom + node.margin.top + self.in_layer_spacing
            for edge in incoming(node):
                if edge.source.owner.type == 'NORTH_SOUTH_PORT':
                    origin = edge.source.owner.properties.get('ORIGIN')
                    result += origin.size.y + origin.margin.bottom + origin.margin.top
        return result

    def dimensions(self):
        if self.widths is None:
            self.widths = [self.layer_width(layer) for layer in self.graph.layers]
            self.heights = [self.layer_height(layer) for layer in self.graph.layers]
        return self.widths, self.heights

    def chunk_count(self):
        widths, heights = self.dimensions()
        maximum = heights[0]
        for value in heights[1:]:
            maximum = _maximum(maximum, value)
        ratio = divide(sum(widths), self.dar * maximum)
        return min(rounded_int(math.sqrt(ratio) if ratio >= 0 else math.nan), self.longest_path)

    def is_cut_allowed(self, index):
        if self.cuts_allowed is None:
            self.cuts_allowed = [False] * self.longest_path
            if 'WRAPPING_VALIDIFY_FORBIDDEN_INDICES' in self.graph.properties:
                for value in read(self.graph, 'WRAPPING_VALIDIFY_FORBIDDEN_INDICES'):
                    if 0 < value < self.longest_path:
                        self.cuts_allowed[value] = False
            else:
                for i, layer in enumerate(self.graph.layers[1:], 1):
                    first = second = None
                    allowed = True
                    for node in layer.nodes:
                        for edge in incoming(node):
                            if (first is not None and first is not node) or (second is not None and second is not edge.source.owner):
                                allowed = False
                                break
                            first, second = node, edge.source.owner
                        if not allowed:
                            break
                    self.cuts_allowed[i] = allowed
        return self.cuts_allowed[index]


def cut_indexes(graph, stats):
    strategy = read(graph, 'WRAPPING_CUTTING_STRATEGY')
    if strategy == 'MANUAL':
        value = read(graph, 'WRAPPING_CUTTING_CUTS')
        return value if value is not None else []
    if strategy == 'ARD':
        rows = stats.chunk_count()
        step = divide(stats.longest_path, rows)
        return [rounded_int(i * step) for i in range(1, rows)]
    widths, heights = stats.dimensions()
    cumulative = [widths[0]]
    total = widths[0]
    for width in widths[1:]:
        cumulative.append(cumulative[-1] + width)
        total += width
    count = stats.chunk_count() - 1
    freedom = read(graph, 'WRAPPING_CUTTING_MSD_FREEDOM')
    best_scale, best = -math.inf, []
    for m in range(max(0, count - freedom), min(stats.longest_path - 1, count + freedom) + 1):
        row_sum = total / (m + 1)
        so_far = last_width = height = 0.0
        width = -math.inf
        row_height = heights[0]
        cuts = []
        if m == 0:
            width, height = total, heights[0]
            for value in heights[1:]:
                height = _maximum(height, value)
        else:
            for i in range(1, stats.longest_path):
                if cumulative[i - 1] - so_far >= row_sum:
                    cuts.append(i)
                    width = _maximum(width, cumulative[i - 1] - last_width)
                    height += row_height
                    so_far += cumulative[i - 1] - so_far
                    last_width = cumulative[i - 1]
                    row_height = heights[i]
                row_height = _maximum(row_height, heights[i])
            height += row_height
        scale = _minimum(divide(1, width), divide(divide(1, stats.dar), height))
        if scale > best_scale:
            best_scale, best = scale, cuts
    return best


def validify_greedily(stats, cuts):
    result = []
    offset = 0
    for value in cuts:
        cut = value + offset
        while cut < stats.longest_path and not stats.is_cut_allowed(cut):
            cut += 1
            offset += 1
        if cut >= stats.longest_path:
            break
        result.append(cut)
    return result


def validify_looking_back(desired, valid):
    result = []
    i = c = offset = 0
    while i < len(valid) - 1 and c < len(desired):
        current = desired[c] + offset
        while valid[i + 1] < current:
            i += 1
        select = 1 if current - valid[i] > valid[i + 1] - current else 0
        chosen = valid[i + select]
        result.append(chosen)
        offset += chosen - current
        c += 1
        while c < len(desired) and desired[c] + offset <= chosen:
            c += 1
        i += 1 + select
    return result


def validify_cuts(graph, stats, cuts):
    strategy = read(graph, 'WRAPPING_VALIDIFY_STRATEGY')
    if strategy == 'GREEDY':
        return validify_greedily(stats, cuts)
    if strategy == 'LOOK_BACK' and cuts:
        valid = [-2147483648] + [i for i in range(1, stats.longest_path) if stats.is_cut_allowed(i)]
        return validify_looking_back(cuts, valid + [2147483647]) if len(valid) > 1 else []
    return cuts


def single_edge_graph_wrapper(graph, *, monitor=None):
    from .cycles_general import reverse_edge
    monitor = monitor if monitor is not None else BasicProgressMonitor()
    monitor.begin('Path-Like Graph Wrapping', 1)
    if not graph.layers:
        monitor.done()
        return
    stats = GraphStats(graph)
    widths, _ = stats.dimensions()
    maximum = widths[0]
    for value in widths[1:]:
        maximum = _maximum(maximum, value)
    if stats.dar > divide(maximum * stats.longest_path, maximum):
        monitor.done()
        return
    cuts = validify_cuts(graph, stats, cut_indexes(graph, stats))
    if cuts:
        iterator = iter(cuts)
        next_cut = next(iterator)
        new_index = 0
        for index in range(stats.longest_path):
            if index == next_cut:
                new_index = 0
                next_cut = next(iterator, stats.longest_path + 1)
            if index != new_index:
                old, new = graph.layers[index], graph.layers[new_index]
                for node in list(old.nodes):
                    set_layer(node, new, len(new.nodes))
                    if new_index == 0:
                        for edge in list(incoming(node)):
                            reverse_edge(edge, True)
                            graph.properties['CYCLIC'] = True
                            insert_dummies(graph, edge, 1)
            new_index += 1
        graph.layers[:] = [layer for layer in graph.layers if layer.nodes]
    monitor.done()
