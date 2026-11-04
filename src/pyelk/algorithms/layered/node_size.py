# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Adapted from fixed elkjs 0.12.1 lib/elk-worker.js (worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86),
# commit 624ae90aa37110033a8af59c5ccbb292708b4317, E13-P04A.
# This independent migration workspace is not the current release package.
"""Port placement over the caller's actual computed node/cell geometry.

The staging data below are native host representations. This module does not
invent minimum cell sizes, implement full NodeContext label policy, or select
an admission domain. Full node-size/cell integration is a separate source block.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .graph import Insets, LNode, LPort, Vec2
from .ports import _divide


@dataclass
class PlacementPortContext:
    port: LPort
    port_position: Vec2 | None = None
    port_margin: Insets = field(default_factory=Insets)
    labels_next_to_port: bool = False
    port_label_cell: Any | None = None

    def __post_init__(self):
        if self.port_position is None:
            self.port_position = Vec2(self.port.pos.x, self.port.pos.y)


@dataclass
class PortPlacementContext:
    node: LNode
    node_size: Vec2
    port_constraints: str
    port_contexts: dict[str, list[PlacementPortContext]]
    # Actual AtomicCell objects supplied by the preceding approved cell chain.
    # Required fields: cell_rectangle, padding, minimum_content_area_size.
    inside_port_label_cells: dict[str, Any]
    port_port_spacing: float
    size_options: set[str] = field(default_factory=set)


def get_port_alignment(context: PortPlacementContext, side: str) -> str:
    alignment = context.node.properties.get("PORT_ALIGNMENT_" + side)
    return alignment if alignment is not None else context.node.properties.get("PORT_ALIGNMENT_DEFAULT", "DISTRIBUTED")


def _horizontal_port_y(port: LPort) -> float:
    if "PORT_BORDER_OFFSET" in port.properties:
        offset = port.properties["PORT_BORDER_OFFSET"]
        return -port.size.y - offset if port.side == "NORTH" else offset
    return -port.size.y if port.side == "NORTH" else 0.0


def calculate_vertical_port_x(context: PlacementPortContext, node_width: float) -> float:
    port = context.port
    if "PORT_BORDER_OFFSET" in port.properties:
        offset = port.properties["PORT_BORDER_OFFSET"]
        return -port.size.x - offset if port.side == "WEST" else node_width + offset
    return -port.size.x if port.side == "WEST" else node_width


def _max_zero(value):
    # Python max(0, nan) does not implement the JS Math.max intrinsic.
    return math.nan if math.isnan(value) else max(0.0, value)


def _place_free(context: PortPlacementContext, side: str, *, vertical: bool):
    ports = context.port_contexts.get(side, ())
    if not ports:
        return
    cell = context.inside_port_label_cells[side]
    rectangle, padding = cell.cell_rectangle, cell.padding
    alignment = get_port_alignment(context, side)
    if vertical:
        available = rectangle.height - padding.top - padding.bottom
        calculated = cell.minimum_content_area_size.y
        current = rectangle.y + padding.top
    else:
        available = rectangle.width - padding.left - padding.right
        calculated = cell.minimum_content_area_size.x
        current = rectangle.x + padding.left
    space_between = context.port_port_spacing
    count = len(ports)
    if alignment in ("DISTRIBUTED", "JUSTIFIED") and count == 1:
        calculated = calculated - 2 * context.port_port_spacing if alignment == "DISTRIBUTED" else calculated
        alignment = "CENTER"
    if available < calculated and "PORTS_OVERHANG" not in context.size_options:
        if alignment == "DISTRIBUTED":
            space_between += _divide(available - calculated, count + 1)
            current += space_between
        else:
            space_between += _divide(available - calculated, count - 1)
    else:
        if available < calculated:
            calculated = calculated - 2 * context.port_port_spacing if alignment == "DISTRIBUTED" else calculated
            alignment = "CENTER"
        if alignment == "CENTER":
            current += (available - calculated) / 2
        elif alignment == "END":
            current += available - calculated
        elif alignment == "DISTRIBUTED":
            additional_space = _divide(available - calculated, count + 1)
            space_between += _max_zero(additional_space)
            current += space_between
        elif alignment == "JUSTIFIED":
            additional_space = _divide(available - calculated, count - 1)
            space_between += _max_zero(additional_space)
    for stage in ports:
        port, margin = stage.port, stage.port_margin
        if vertical:
            stage.port_position.x = calculate_vertical_port_x(stage, context.node_size.x)
            stage.port_position.y = current + margin.top
            current += margin.top + port.size.y + margin.bottom + space_between
        else:
            stage.port_position.x = current + margin.left
            stage.port_position.y = _horizontal_port_y(port)
            current += margin.left + port.size.x + margin.right + space_between


def place_horizontal_ports(context: PortPlacementContext) -> None:
    """Source width-known step; SOUTH y remains relative to its bottom edge."""
    for side in ("NORTH", "SOUTH"):
        if context.port_constraints in ("FIXED_POS", "FIXED_RATIO"):
            for stage in context.port_contexts.get(side, ()):
                if context.port_constraints == "FIXED_RATIO":
                    stage.port_position.x = context.node_size.x * stage.port.properties["PORT_RATIO_OR_POSITION"]
                stage.port_position.y = _horizontal_port_y(stage.port)
        else:
            _place_free(context, side, vertical=False)


def offset_southern_ports_by_node_size(context: PortPlacementContext) -> None:
    """Run only after the caller has computed the actual node height."""
    for stage in context.port_contexts.get("SOUTH", ()):
        stage.port_position.y += context.node_size.y


def place_vertical_ports(context: PortPlacementContext) -> None:
    for side in ("EAST", "WEST"):
        if context.port_constraints in ("FIXED_POS", "FIXED_RATIO"):
            for stage in context.port_contexts.get(side, ()):
                stage.port_position.x = calculate_vertical_port_x(stage, context.node_size.x)
                if context.port_constraints == "FIXED_RATIO":
                    stage.port_position.y = context.node_size.y * stage.port.properties["PORT_RATIO_OR_POSITION"]
        else:
            _place_free(context, side, vertical=True)


def apply_port_positions(context: PortPlacementContext) -> None:
    """Value-copy staged geometry; preserve original position object identity."""
    for side in ("NORTH", "EAST", "SOUTH", "WEST"):
        for stage in context.port_contexts.get(side, ()):
            stage.port.pos.x, stage.port.pos.y = stage.port_position.x, stage.port_position.y


_CONTEXT_IDS = {
    "NODE_LABELS_PADDING": "org.eclipse.elk.nodeLabels.padding",
    "SPACING_LABEL_NODE": "org.eclipse.elk.spacing.labelNode",
    "SPACING_LABEL_LABEL": "org.eclipse.elk.spacing.labelLabel",
    "SPACING_PORT_PORT": "org.eclipse.elk.spacing.portPort",
    "SPACING_LABEL_PORT_HORIZONTAL": "org.eclipse.elk.spacing.labelPortHorizontal",
    "SPACING_LABEL_PORT_VERTICAL": "org.eclipse.elk.spacing.labelPortVertical",
    "SPACING_PORTS_SURROUNDING": "org.eclipse.elk.spacing.portsSurrounding",
}
_SPACING_DEFAULTS = {"SPACING_LABEL_NODE": 5, "SPACING_LABEL_LABEL": 0,
                     "SPACING_PORT_PORT": 10, "SPACING_LABEL_PORT_HORIZONTAL": 1,
                     "SPACING_LABEL_PORT_VERTICAL": 1}


def individual_or_inherited(node: LNode, name: str):
    """Source individual holder -> graph -> declared default, preserving0.

    The central typed layer supplies canonical-ID keys in individual holders.
    A direct node spacing property is deliberately not another inheritance
    level. Graph internal properties precede its canonical typed options.
    """
    canonical = _CONTEXT_IDS[name]
    individual = node.properties.get("SPACING_INDIVIDUAL")
    result = None if individual is None else individual.get(canonical)
    if result is None:
        graph = node.graph
        if graph is not None:
            result = graph.properties.get(name)
            if result is None and graph.options is not None:
                result = graph.options.values.get(canonical)
    if result is not None:
        return result
    if name == "NODE_LABELS_PADDING":
        return Insets(5, 5, 5, 5)
    if name == "SPACING_PORTS_SURROUNDING":
        return Insets()
    return _SPACING_DEFAULTS[name]


def valid_node_label_placement(placement) -> bool:
    return all(len(set(placement).intersection(group)) <= 1 for group in (
        {"INSIDE", "OUTSIDE"}, {"H_LEFT", "H_CENTER", "H_RIGHT"},
        {"V_TOP", "V_CENTER", "V_BOTTOM"}))


def valid_port_label_placement(placement) -> bool:
    return all(len(set(placement).intersection(group)) <= 1 for group in (
        {"INSIDE", "OUTSIDE"},
        {"ALWAYS_SAME_SIDE", "ALWAYS_OTHER_SAME_SIDE", "SPACE_EFFICIENT"}))


class NodeContext(PortPlacementContext):
    """P04B context construction; no size/label placement is run here.

    ``adapted_port_edges`` supplies actual source-adapter edge views when
    north/south or self-loop preprocessing changes native adjacency. These
    adapters are separate pending callers, never assumed to have empty edges.
    """
    def __init__(self, node: LNode, *, adapted_port_edges=None,
                 transparent_north_south_edges: bool = True):
        from .cell_layout import CENTER, HORIZONTAL, VERTICAL, StripContainerCell
        from ..._errors import UnsupportedFeatureError
        props = node.properties
        size_options = set(props.get("NODE_SIZE_OPTIONS", {"DEFAULT_MINIMUM_SIZE"}))
        super().__init__(node, Vec2(node.size.x, node.size.y),
                         props.get("PORT_CONSTRAINTS", "UNDEFINED"), {}, {},
                         individual_or_inherited(node, "SPACING_PORT_PORT"), size_options)
        self.topdown_layout = props.get("TOPDOWN_LAYOUT", False)
        self.treat_as_compound_node = bool(props.get("COMPOUND_NODE", False)
                                           or props.get("INSIDE_SELF_LOOPS_ACTIVATE", False))
        self.size_constraints = set(props.get("NODE_SIZE_CONSTRAINTS", ()))
        self.port_labels_placement = set(props.get("PORT_LABELS_PLACEMENT", {"OUTSIDE"}))
        self.node_label_placement = set(props.get("NODE_LABELS_PLACEMENT", ()))
        if not valid_port_label_placement(self.port_labels_placement):
            raise UnsupportedFeatureError("UNSUPPORTED_CONFIGURATION", "", "Invalid port label placement")
        if not valid_node_label_placement(self.node_label_placement):
            raise UnsupportedFeatureError("UNSUPPORTED_CONFIGURATION", "", "Invalid node label placement")
        self.port_labels_treat_as_group = props.get("PORT_LABELS_TREAT_AS_GROUP", True)
        self.node_labels_padding = individual_or_inherited(node, "NODE_LABELS_PADDING")
        self.node_label_spacing = individual_or_inherited(node, "SPACING_LABEL_NODE")
        self.label_label_spacing = individual_or_inherited(node, "SPACING_LABEL_LABEL")
        self.port_label_spacing_horizontal = individual_or_inherited(node, "SPACING_LABEL_PORT_HORIZONTAL")
        self.port_label_spacing_vertical = individual_or_inherited(node, "SPACING_LABEL_PORT_VERTICAL")
        self.surrounding_port_margins = individual_or_inherited(node, "SPACING_PORTS_SURROUNDING")
        self.label_cell_spacing = 2 * self.label_label_spacing
        symmetrical = "ASYMMETRICAL" not in self.size_options
        self.node_container = StripContainerCell(VERTICAL, symmetrical, 0)
        self.node_container_middle_row = StripContainerCell(HORIZONTAL, symmetrical, 0)
        self.node_container.set_cell(CENTER, self.node_container_middle_row)
        self.outside_node_label_containers = {}
        self.node_label_cells = {}
        self.adapted_port_edges = adapted_port_edges
        # LabelAndNodeSizeProcessor's actual LGraphAdapter caller supplies true;
        # other approved callers must preserve their own adapter flag.
        self.transparent_north_south_edges = transparent_north_south_edges


def create_port_contexts(context: NodeContext, ignore_inside_port_labels: bool = False) -> None:
    """Create real LabelCells, assign volatile IDs, preserve source group order."""
    from .cell_layout import LabelCell
    from ..._errors import UnsupportedFeatureError
    placement = context.port_labels_placement
    import_labels = not ignore_inside_port_labels or "INSIDE" not in placement
    fixed_labels = "INSIDE" not in placement and "OUTSIDE" not in placement
    for volatile_id, port in enumerate(context.node.ports):
        if port.side == "UNDEFINED":
            raise ValueError("Label and node size calculator requires assigned port sides")
        port.id = volatile_id
        stage = PlacementPortContext(port)
        next_to_port = "NEXT_TO_PORT_IF_POSSIBLE" in placement
        if "INSIDE" in placement:
            stage.labels_next_to_port = (next_to_port and not port.properties.get("INSIDE_CONNECTIONS", False)
                                         if context.treat_as_compound_node else True)
        elif "OUTSIDE" in placement and next_to_port:
            if (context.transparent_north_south_edges
                    and port.owner.type == "NORTH_SOUTH_PORT"):
                # Both original adapter accessors return EMPTY before reading
                # raw adjacency, portDummy or the self-loop holder in this case.
                incoming, outgoing = (), ()
            elif context.adapted_port_edges is not None:
                incoming, outgoing = context.adapted_port_edges[port]
            else:
                if ((context.transparent_north_south_edges and port.properties.get("PORT_DUMMY") is not None)
                        or context.node.properties.get("SELF_LOOP_HOLDER") is not None):
                    raise UnsupportedFeatureError("UNSUPPORTED_NODE_CONTEXT_ADAPTER", "",
                                                  "North/south and self-loop contexts require actual adapted edge views")
                incoming, outgoing = port.incoming_edges, port.outgoing_edges
            stage.labels_next_to_port = not (incoming or outgoing)
        context.port_contexts.setdefault(port.side, []).append(stage)
        if import_labels and not fixed_labels:
            stage.port_label_cell = LabelCell(context.label_label_spacing)
            for label in getattr(port, "labels", ()):
                stage.port_label_cell.add_label(label)
    # The source TreeMultimap compares side ordinal and assigned volatile ID;
    # IDs are unique within this creator. No generic Guava map is ported.
    context.port_contexts = {side: context.port_contexts[side]
                             for side in ("NORTH", "EAST", "SOUTH", "WEST")
                             if side in context.port_contexts}
    for side in ("SOUTH", "WEST"):
        if side in context.port_contexts:
            context.port_contexts[side].reverse()
