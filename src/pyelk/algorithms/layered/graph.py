# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Host representation of elkjs 0.12.1 generated layered graph structures.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# lib/elk-worker.js SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Component mapping: references/e04-source-components-A.json
# Exact external Java build identity is unresolved. See pyelk/_licenses/NOTICE.md.
"""Mutable ordered algorithm graph data; this module computes no layout.

Relationships are established explicitly by the setters, as in the generated
source. Constructors only store fields. Reassigning the same source/target,
owner or layer removes and appends it again, preserving the source move-to-tail
semantics rather than silently treating assignment as a no-op.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...model import Edge, Graph, Node, Port
from ...options import ResolvedOptions


@dataclass(eq=False)
class Vec2:
    x: float = 0.0
    y: float = 0.0


@dataclass(eq=False)
class Insets:
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0


@dataclass(eq=False)
class LGraph:
    origin: Graph
    options: ResolvedOptions
    random: Any
    layerless_nodes: list[LNode] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    size: Vec2 = field(default_factory=Vec2)
    offset: Vec2 = field(default_factory=Vec2)
    padding: Insets = field(default_factory=Insets)
    properties: dict[str, Any] = field(default_factory=dict)
    # Source graph-element scratch ID; separate from origin.id/public JSON.
    id: int = 0


@dataclass(eq=False)
class LNode:
    graph: LGraph
    origin: Node | None = None
    id: int = 0
    type: str = "NORMAL"
    pos: Vec2 = field(default_factory=Vec2)
    size: Vec2 = field(default_factory=Vec2)
    margin: Insets = field(default_factory=Insets)
    padding: Insets = field(default_factory=Insets)
    ports: list[LPort] = field(default_factory=list)
    layer: Layer | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    port_sides_cached: bool = False
    port_side_indices: dict[str, tuple[int, int]] = field(default_factory=dict)
    labels: list[Any] = field(default_factory=list)


@dataclass(eq=False)
class LPort:
    owner: LNode | None = None
    origin: Port | None = None
    id: int = 0
    side: str = "UNDEFINED"
    pos: Vec2 = field(default_factory=Vec2)
    size: Vec2 = field(default_factory=Vec2)
    anchor: Vec2 = field(default_factory=Vec2)
    incoming_edges: list[LEdge] = field(default_factory=list)
    outgoing_edges: list[LEdge] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    # Fixed source LPort prototype; setSide preserves a supplied anchor.
    explicitly_supplied_port_anchor: bool = False
    labels: list[Any] = field(default_factory=list)


@dataclass(eq=False)
class LEdge:
    origin: Edge | None = None
    id: int = 0
    source: LPort | None = None
    target: LPort | None = None
    bend_points: list[Vec2] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    labels: list[Any] = field(default_factory=list)


@dataclass(eq=False)
class Layer:
    graph: LGraph
    nodes: list[LNode] = field(default_factory=list)
    size: Vec2 = field(default_factory=Vec2)
    id: int = 0


def _remove_identity(items, value):
    for index, item in enumerate(items):
        if item is value:
            del items[index]
            return


def set_source(edge: LEdge, port: LPort | None) -> None:
    """Mirror worker $setSource_0, including same-port move-to-tail."""
    if not isinstance(edge, LEdge) or (port is not None and not isinstance(port, LPort)):
        raise TypeError("Expected an LEdge and an optional LPort")
    if edge.source is not None:
        _remove_identity(edge.source.outgoing_edges, edge)
    edge.source = port
    if port is not None:
        port.outgoing_edges.append(edge)


def set_target(edge: LEdge, port: LPort | None) -> None:
    """Mirror worker $setTarget_0 using incoming adjacency."""
    if not isinstance(edge, LEdge) or (port is not None and not isinstance(port, LPort)):
        raise TypeError("Expected an LEdge and an optional LPort")
    if edge.target is not None:
        _remove_identity(edge.target.incoming_edges, edge)
    edge.target = port
    if port is not None:
        port.incoming_edges.append(edge)


def set_target_and_insert_at_index(edge: LEdge, port: LPort | None, index: int) -> None:
    """Mirror worker $setTargetAndInsertAtIndex for valid source calls.

    This E05 host addition validates an invalid insertion atomically. The source
    join call records the dropped edge's destination index before inserting its
    survivor; replacing this operation with append would change adjacency order.
    """
    if not isinstance(edge, LEdge) or (port is not None and not isinstance(port, LPort)):
        raise TypeError("Expected an LEdge and an optional LPort")
    if type(index) is not int:
        raise TypeError("Expected an integer target index")
    if index < 0:
        raise ValueError("Target index is negative")
    if port is not None:
        count = len(port.incoming_edges) - sum(item is edge for item in port.incoming_edges)
        if index > count:
            raise ValueError("Target index is outside the final insertion range")
    if edge.target is not None:
        _remove_identity(edge.target.incoming_edges, edge)
    edge.target = port
    if port is not None:
        port.incoming_edges.insert(index, edge)


def set_port_owner(port: LPort, owner: LNode | None) -> None:
    """Mirror worker $setNode without changing edge endpoints."""
    if not isinstance(port, LPort) or (owner is not None and not isinstance(owner, LNode)):
        raise TypeError("Expected an LPort and an optional LNode")
    if port.owner is not None:
        _remove_identity(port.owner.ports, port)
    port.owner = owner
    if owner is not None:
        owner.ports.append(port)


def set_layer(node: LNode, layer: Layer | None, index: int | None = None) -> None:
    """Move a node's ordered layer membership; graph ownership is separate.

    Source setLayer removes and appends, and its indexed variant inserts at the
    requested position. The host API rejects invalid final insertion positions
    before mutation, keeping a bad internal call from leaving half a relation.
    It does not add/remove layerless_nodes; that is a separate source operation.
    """
    if not isinstance(node, LNode) or (layer is not None and not isinstance(layer, Layer)):
        raise TypeError("Expected an LNode and an optional Layer")
    if index is not None:
        if type(index) is not int:
            raise TypeError("Layer index must be an integer")
        if layer is None:
            raise ValueError("An indexed insertion requires a layer")
        count = len(layer.nodes) - sum(item is node for item in layer.nodes)
        if index < 0 or index > count:
            raise ValueError("Layer index is outside the final insertion range")
    if node.layer is not None:
        _remove_identity(node.layer.nodes, node)
    node.layer = layer
    if layer is not None:
        if index is None:
            layer.nodes.append(node)
        else:
            layer.nodes.insert(index, node)
