# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Ported from the fixed elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Components: references/e05-source-components-A.json, approved E05 split/join.
# E06 orientation/multiplicity/scale: references/e06-source-components-A.json.
# Exact external Java build remains unresolved. See pyelk/_licenses/NOTICE-E06.md.
"""Source long-edge links and restoration; no oracle or public JSON dispatch."""
import math

from ..._errors import UnsupportedFeatureError
from .graph import LEdge, LGraph, LNode, LPort, Vec2, set_layer, set_port_owner, set_source, set_target, set_target_and_insert_at_index


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_SLICE", "", message)


def _layer_nodes(graph):
    if not isinstance(graph, LGraph):
        raise TypeError("Expected an LGraph")
    nodes = [node for layer in graph.layers for node in layer.nodes]
    if len({id(node) for node in nodes}) != len(nodes):
        _outside("Long-edge layers contain a duplicate node identity")
    if len(graph.layers) > 8 or len(nodes) > 176 or sum(node.type == "NORMAL" for node in nodes) > 8:
        _outside("The reviewed long-edge scope has at most eight original nodes and 176 internal nodes")
    ports, edges = set(), set()
    for layer in graph.layers:
        if layer.graph is not graph:
            _outside("Layer graph ownership differs")
        for node in layer.nodes:
            if node.graph is not graph or node.layer is not layer or node.type not in ("NORMAL", "LONG_EDGE"):
                _outside("Unreviewed node type or layer ownership")
            for port in node.ports:
                if port.owner is not node or port in ports:
                    _outside("Long-edge port ownership or identity is inconsistent")
                ports.add(port)
                for edge in port.outgoing_edges:
                    if (edge in edges or edge.source is not port or edge.target is None
                            or edge.target.owner not in nodes or edge.target not in edge.target.owner.ports
                            or sum(item is edge for item in edge.target.incoming_edges) != 1):
                        _outside("Long-edge endpoint adjacency is inconsistent")
                    edges.add(edge)
    if len(ports) > 392 or len(edges) > 196:
        _outside("The reviewed long-edge work graph has at most 392 ports and 196 segments")
    return nodes


def get_junction_points(edge):
    """Source mutable default: materialize a distinct empty chain per holder.

    Property.getDefault clones KVectorChain; PropertyHolder.getProperty stores
    that clone. A present empty chain is a Java object, so it is not a false
    default. Calling this getter is itself a real property write when absent.
    """
    if not isinstance(edge, LEdge):
        raise TypeError("Expected an LEdge")
    value = edge.properties.get("JUNCTION_POINTS")
    if value is None:
        value = []
        edge.properties["JUNCTION_POINTS"] = value
    if type(value) is not list or any(not isinstance(point, Vec2) for point in value):
        _outside("Junction points require an ordered vector chain")
    return value


def _dummy_port(node, side, position):
    # Source new LPort + setSide + setNode. Both size and anchor start at zero.
    port = LPort()
    port.side = side
    set_port_owner(port, node)
    port.pos.y = position
    return port


def split_edge(edge, dummy):
    """Source splitEdge, guarded to E05's fixed default thickness and no labels."""
    if edge.source is None or edge.target is None:
        _outside("Cannot split a detached edge")
    thickness = edge.properties.get("EDGE_THICKNESS", 1)
    if type(thickness) not in (int, float) or not math.isfinite(thickness) or thickness != 1:
        _outside("Custom edge thickness is outside this E05 source approval")
    old_target = edge.target
    dummy.size.y = thickness
    port_position = math.floor(thickness / 2)
    incoming = _dummy_port(dummy, "WEST", port_position)
    outgoing = _dummy_port(dummy, "EAST", port_position)
    set_target(edge, incoming)
    # ORIGIN for an edge remains the same original model edge. The dictionary
    # copy is shallow: referenced property values are deliberately shared.
    generated = LEdge(origin=edge.origin, properties=dict(edge.properties))
    generated.properties.pop("JUNCTION_POINTS", None)
    set_source(generated, outgoing)
    set_target(generated, old_target)
    source_node, target_node = edge.source.owner, generated.target.owner
    if source_node.type == "LONG_EDGE":
        dummy.properties["LONG_EDGE_SOURCE"] = source_node.properties["LONG_EDGE_SOURCE"]
        dummy.properties["LONG_EDGE_TARGET"] = source_node.properties["LONG_EDGE_TARGET"]
        dummy.properties["LONG_EDGE_HAS_LABEL_DUMMIES"] = source_node.properties.get("LONG_EDGE_HAS_LABEL_DUMMIES", False)
    elif source_node.type == "NORMAL" and target_node.type in ("NORMAL", "LONG_EDGE"):
        dummy.properties["LONG_EDGE_SOURCE"] = edge.source
        dummy.properties["LONG_EDGE_TARGET"] = generated.target
    else:
        _outside("Label dummy propagation is outside E05")
    # moveHeadLabels has no iterations: admitted input has no labels and no
    # earlier processor in this slice creates label objects or label dummies.
    return generated


def long_edge_splitter(graph):
    """Source $process_35: append a real dummy at every intermediate rank."""
    _layer_nodes(graph)
    if len(graph.layers) <= 2:
        return
    for index in range(len(graph.layers) - 1):
        layer, following = graph.layers[index:index + 2]
        for node in layer.nodes:
            for port in node.ports:
                for edge in list(port.outgoing_edges):
                    if edge.target is None or edge.target.owner is None:
                        _outside("A source long edge must have an attached target")
                    target_layer = edge.target.owner.layer
                    if target_layer is not layer and target_layer is not following:
                        if target_layer not in graph.layers[index + 2:]:
                            _outside("E05 splitting requires a forward layer edge")
                        dummy = LNode(graph, type="LONG_EDGE")
                        dummy.properties["ORIGIN"] = edge
                        dummy.properties["PORT_CONSTRAINTS"] = "FIXED_POS"
                        set_layer(dummy, following)
                        split_edge(edge, dummy)


def _absolute_anchor(port):
    x, y = 0.0, 0.0
    for vector in (port.owner.pos, port.pos, port.anchor):
        x += vector.x
        y += vector.y
    return Vec2(x, y)


def join_at(dummy, *, add_unnecessary_bendpoints=False):
    """Source joinAt: preserve target index, segment order and mutable defaults."""
    west = [port for port in dummy.ports if port.side == "WEST"]
    east = [port for port in dummy.ports if port.side == "EAST"]
    if len(west) != 1 or len(east) != 1 or len(west[0].incoming_edges) != len(east[0].outgoing_edges):
        _outside("Unreviewed long-edge dummy port/chain shape")
    incoming, outgoing = west[0].incoming_edges, east[0].outgoing_edges
    unnecessary = _absolute_anchor(dummy.ports[0])
    for _ in range(len(incoming)):
        survivor, dropped = incoming[0], outgoing[0]
        target = dropped.target
        if target is None:
            _outside("Cannot join a detached segment")
        target_index = next(i for i, edge in enumerate(target.incoming_edges) if edge is dropped)
        set_target_and_insert_at_index(survivor, target, target_index)
        set_source(dropped, None)
        set_target(dropped, None)
        if add_unnecessary_bendpoints:
            survivor.bend_points.append(Vec2(unnecessary.x, unnecessary.y))
        for point in dropped.bend_points:
            survivor.bend_points.append(Vec2(point.x, point.y))
        # The no-label guard makes the source label-copy loop empty.
        surviving_junctions = get_junction_points(survivor)
        dropped_junctions = get_junction_points(dropped)
        # Source object truthiness is preserved even for empty chains: both
        # reads above must run and materialize their own default when absent.
        for point in dropped_junctions:
            surviving_junctions.append(Vec2(point.x, point.y))


def long_edge_joiner(graph):
    """Source $process_34: remove LONG_EDGE nodes from layers after restoration."""
    _layer_nodes(graph)
    if graph.properties.get("UNNECESSARY_BENDPOINTS", False) is not False:
        _outside("Unnecessary bendpoints are outside E05 default options")
    for layer in graph.layers:
        index = 0
        while index < len(layer.nodes):
            node = layer.nodes[index]
            if node.type == "LONG_EDGE":
                join_at(node)
                # The source iterator removes membership but does not reset
                # the orphan's layer field at this point.
                del layer.nodes[index]
            else:
                index += 1
