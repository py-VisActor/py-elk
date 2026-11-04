# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Mechanical port from elkjs 0.12.1 generated lib/elk-worker.js.
# Source commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Components/spans: references/e07-source-components-B.json.
# Exact external Java build is unresolved. See pyelk/_licenses/NOTICE-E07.md.
"""Guarded source component DFS, stable row placement and graph finalization.

Preparation, direction transforms and the per-component phase sequence belong
to the caller. These operations retain original objects and shallow property
references; they neither choose a phase nor initialize/draw a random stream.
"""
from functools import cmp_to_key
import math

from ..._errors import UnsupportedFeatureError
from .graph import Insets, LEdge, LGraph, LNode, LPort, Vec2, set_layer
from .long_edges import get_junction_points

_P = "org.eclipse.elk."
_ASPECT_RATIO = 1.600000023841858


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PHASE_INPUT", "", message)


def _finite(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _outside("Component geometry requires finite numbers")
    return value


def _vector(vector):
    if not isinstance(vector, Vec2):
        _outside("Component geometry requires Vec2 objects")
    _finite(vector.x)
    _finite(vector.y)


def _nodes(graph, *, layers=False):
    if not isinstance(graph, LGraph):
        raise TypeError("Expected an LGraph")
    if not isinstance(graph.properties, dict):
        _outside("Component properties require a dictionary")
    if "EXTERNAL_PORTS" in graph.properties.get("GRAPH_PROPERTIES", set()):
        _outside("External-port component placers are outside this source slice")
    if graph.properties.get("CONSIDER_MODEL_ORDER_COMPONENTS", "NONE") != "NONE":
        _outside("Non-default component model ordering is outside this slice")
    if graph.layers and not layers:
        _outside("Expected an ordered layerless component graph")
    if len(graph.layers) > 8:
        _outside("The reviewed component has at most eight layers")
    nodes = list(graph.layerless_nodes)
    for node in nodes:
        if node.layer is not None:
            _outside("Layerless node has a layer pointer")
    for layer in graph.layers:
        if layer.graph is not graph:
            _outside("Component layer ownership differs")
        for node in layer.nodes:
            if node.layer is not layer:
                _outside("Component layer membership differs")
            nodes.append(node)
    if len(nodes) > 8 or len(set(nodes)) != len(nodes):
        _outside("The reviewed completed/raw graph has at most eight distinct nodes")
    for node in nodes:
        if not isinstance(node, LNode) or node.type != "NORMAL" or node.graph is not graph:
            _outside("Component nodes require original NORMAL graph ownership")
    members, ports, outgoing, incoming = set(nodes), set(), set(), set()
    for node in nodes:
        for port in node.ports:
            if not isinstance(port, LPort) or port.owner is not node or port in ports:
                _outside("Component port ownership or identity differs")
            ports.add(port)
            if len(port.incoming_edges) + len(port.outgoing_edges) != 1:
                _outside("The reviewed implicit port has exactly one edge endpoint")
            for edge in port.incoming_edges:
                if (not isinstance(edge, LEdge) or edge in incoming or edge.target is not port
                        or edge.source is None or edge.source.owner not in members
                        or edge.source not in edge.source.owner.ports
                        or sum(item is edge for item in edge.source.outgoing_edges) != 1):
                    _outside("Component incoming adjacency differs")
                incoming.add(edge)
            for edge in port.outgoing_edges:
                if (not isinstance(edge, LEdge) or edge in outgoing or edge.source is not port
                        or edge.target is None or edge.target.owner not in members
                        or edge.target not in edge.target.owner.ports
                        or sum(item is edge for item in edge.target.incoming_edges) != 1):
                    _outside("Component outgoing adjacency differs")
                outgoing.add(edge)
    if incoming != outgoing or len(outgoing) > 28 or len(ports) > 56:
        _outside("Component original edge/port denominator differs from the reviewed bound")
    return nodes


def _padding(graph):
    value = graph.padding
    if not isinstance(value, Insets):
        _outside("Component padding requires Insets")
    for name in ("left", "right", "top", "bottom"):
        if _finite(getattr(value, name)) < 0:
            _outside("Component padding is nonnegative")


def _movable(graph, nodes):
    _vector(graph.offset)
    _vector(graph.size)
    if graph.size.x < 0 or graph.size.y < 0:
        _outside("Completed component rectangles are nonnegative")
    _padding(graph)
    for node in nodes:
        _vector(node.pos)
        for port in node.ports:
            for edge in port.outgoing_edges:
                if not isinstance(edge.bend_points, list):
                    _outside("Component bends require an ordered vector list")
                for point in edge.bend_points:
                    _vector(point)
                if "JUNCTION_POINTS" in edge.properties:
                    points = edge.properties["JUNCTION_POINTS"]
                    if not isinstance(points, list):
                        _outside("An explicit junction chain requires an ordered vector list")
                    for point in points:
                        _vector(point)


def split_components(target):
    """Worker ComponentsProcessor.split/ordered DFS; false returns target itself."""
    nodes = _nodes(target)
    _padding(target)
    separate = target.options.values[_P + "separateConnectedComponents"]
    if type(separate) is not bool:
        _outside("Component separation requires a resolved boolean")
    if not separate:
        return [target]
    for node in nodes:
        node.id = 0
    result = []

    def visit(node, members):
        if node.id != 0:
            return
        node.id = 1
        members.append(node)
        for port in node.ports:
            for edge in port.incoming_edges:
                visit(edge.source.owner, members)
            for edge in port.outgoing_edges:
                visit(edge.target.owner, members)

    for node in nodes:
        if node.id != 0:
            continue
        members = []
        visit(node, members)
        component = LGraph(origin=target.origin, options=target.options, random=target.random,
                           properties=dict(target.properties))
        component.properties["EXT_PORT_CONNECTIONS"] = set()
        component.padding.left = target.padding.left
        component.padding.right = target.padding.right
        component.padding.top = target.padding.top
        component.padding.bottom = target.padding.bottom
        # Source setProperty(null) removes this property instead of storing null.
        component.properties.pop("NODE_SIZE_MINIMUM", None)
        for member in members:
            component.layerless_nodes.append(member)
            member.graph = component
        result.append(component)
    return result


def finish_component(component):
    """The literal ordered cleanup at the end of ElkLayered.layout_1."""
    _nodes(component, layers=True)
    for layer in component.layers:
        component.layerless_nodes.extend(layer.nodes)
        layer.nodes.clear()
    for node in component.layerless_nodes:
        set_layer(node, None)
    component.layers.clear()


def _offset_nodes(graph, offset):
    for node in graph.layerless_nodes:
        node.pos.x += offset.x
        node.pos.y += offset.y
        for port in node.ports:
            for edge in port.outgoing_edges:
                for point in edge.bend_points:
                    point.x += offset.x
                    point.y += offset.y
                # Even an empty Java chain is an existing object. Reading it
                # here performs the real approved clone/store when absent.
                for point in get_junction_points(edge):
                    point.x += offset.x
                    point.y += offset.y


def _move_graph(target, source):
    # add_18 mutates the actual offset before its use as the vector. Keep both
    # +0 writes and every subsequent node/bend/junction +0 (signed-zero effect).
    source.offset.x += 0.0
    source.offset.y += 0.0
    _offset_nodes(source, source.offset)
    for node in source.layerless_nodes:
        target.layerless_nodes.append(node)
        node.graph = target


def _double_compare(left, right):
    if left < right:
        return -1
    if left > right:
        return 1
    if left == right:
        if left == 0:
            a, b = math.copysign(1.0, left), math.copysign(1.0, right)
            return -1 if a < b else 1 if a > b else 0
        return 0
    return 0 if math.isnan(left) and math.isnan(right) else 1 if math.isnan(left) else -1


def _maximum(left, right):
    if left == right == 0:
        return 0.0 if math.copysign(1.0, left) > 0 or math.copysign(1.0, right) > 0 else -0.0
    return left if left >= right else right


def combine_components(components, target):
    """Source SimpleRowGraphPlacer.combine, including stable sort and two moves."""
    if not isinstance(components, list) or not isinstance(target, LGraph):
        raise TypeError("Expected an ordered component list and an LGraph target")
    if len(components) > 8 or len(set(components)) != len(components):
        _outside("At most eight distinct component graphs are reviewed")
    nodes, all_nodes = {}, set()
    for graph in components:
        current = _nodes(graph)
        _movable(graph, current)
        if all_nodes.intersection(current):
            _outside("Component graphs repeat an original node")
        all_nodes.update(current)
        nodes[graph] = current
        if graph.origin is not target.origin or graph.random is not target.random:
            _outside("Component origin/random identity differs from global preparation")
    if len(all_nodes) > 8 or sum(len(node.ports) for node in all_nodes) > 56:
        _outside("Global component node/port denominator exceeds the reviewed bound")
    if len(components) == 1:
        source = components[0]
        if source is not target:
            target.layerless_nodes.clear()
            _move_graph(target, source)
            target.properties.update(source.properties)
            target.padding.left = source.padding.left
            target.padding.right = source.padding.right
            target.padding.top = source.padding.top
            target.padding.bottom = source.padding.bottom
            target.size.x, target.size.y = source.size.x, source.size.y
        return
    if not components:
        target.layerless_nodes.clear()
        target.size.x = 0.0
        target.size.y = 0.0
        return
    if target in components:
        _outside("The multi-component target is separate from all work graphs")
    if target.properties.get("CONSIDER_MODEL_ORDER_COMPONENTS", "NONE") != "NONE":
        _outside("Only default component ordering is reviewed")
    area_guard = 0.0
    for graph in components:
        if graph.properties.get("COMPACTION_CONNECTED_COMPONENTS", False) is not False:
            _outside("Component compaction is outside the reviewed source branch")
        for node in graph.layerless_nodes:
            priority = node.properties.get("PRIORITY", 0)
            if type(priority) is not int or priority != 0:
                _outside("Only default node priority is reviewed")
        area_guard += _finite(graph.size.x * graph.size.y)
        _finite(area_guard)
    spacing = target.options.values[_P + "spacing.componentComponent"]
    if _finite(spacing) < 0:
        _outside("Component spacing is nonnegative")
    for graph in components:
        priority = 0
        for node in graph.layerless_nodes:
            priority += node.properties.get("PRIORITY", 0)
        graph.id = priority

    def compare(a, b):
        priority = b.id - a.id
        return priority if priority else _double_compare(a.size.x * a.size.y, b.size.x * b.size.y)

    components.sort(key=cmp_to_key(compare))
    first = components[0]
    target.layerless_nodes.clear()
    target.properties.update(first.properties)
    max_row_width = 0.0
    total_area = 0.0
    for graph in components:
        max_row_width = _maximum(max_row_width, graph.size.x)
        total_area += graph.size.x * graph.size.y
    max_row_width = _maximum(max_row_width, math.sqrt(total_area) * _ASPECT_RATIO)
    xpos = 0.0
    ypos = 0.0
    highest_box = 0.0
    broadest_row = spacing
    for graph in components:
        if xpos + graph.size.x > max_row_width:
            xpos = 0.0
            ypos += highest_box + spacing
            highest_box = 0.0
        _offset_nodes(graph, Vec2(xpos + graph.offset.x, ypos + graph.offset.y))
        graph.offset.x = 0.0
        graph.offset.y = 0.0
        broadest_row = _maximum(broadest_row, xpos + graph.size.x)
        highest_box = _maximum(highest_box, graph.size.y)
        xpos += graph.size.x + spacing
    target.size.x = broadest_row
    target.size.y = ypos + highest_box
    for graph in components:
        _move_graph(target, graph)


def resize_graph(target):
    """Source resizeGraph's default constraint branch and literal add/subtract."""
    if not isinstance(target, LGraph):
        raise TypeError("Expected an LGraph")
    _vector(target.size)
    _vector(target.offset)
    _padding(target)
    for key, default in (("NODE_SIZE_CONSTRAINTS", frozenset()),
                         ("NODE_SIZE_OPTIONS", frozenset({"DEFAULT_MINIMUM_SIZE"})),
                         ("CONTENT_ALIGNMENT", frozenset({"V_TOP", "H_LEFT"}))):
        value = target.properties.get(key, default)
        if type(value) not in (set, frozenset) or value != default:
            _outside("Non-default graph sizing/alignment is outside this branch")
    if target.properties.get("NODE_SIZE_FIXED_GRAPH_SIZE", False) is not False:
        _outside("Fixed graph size is outside this branch")
    calculated = Vec2(target.size.x + target.padding.left + target.padding.right,
                      target.size.y + target.padding.top + target.padding.bottom)
    _vector(calculated)
    adjusted = Vec2(calculated.x, calculated.y)
    # The default empty constraints never grow adjustedSize. Neither its
    # EnumSet nor options/alignment implements type4 in the fixed worker, so
    # these missing reads remain absent rather than cloning/storing sets.
    target.size.x = adjusted.x - target.padding.left - target.padding.right
    target.size.y = adjusted.y - target.padding.top - target.padding.bottom
