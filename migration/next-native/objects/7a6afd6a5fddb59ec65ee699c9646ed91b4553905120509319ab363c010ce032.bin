# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Constrained port of elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Component/guard map: references/e04-source-components-A.json
# E05 approved component deltas: references/e05-source-components-A.json.
# E06 NORTH/scans/configuration: references/e06-source-components-R.json.
# E06 loop delegates: references/e06-source-components-B.json; NOTICE-E06.md.
# Exact external Java build is unresolved. See pyelk/_licenses/NOTICE.md.
"""Seventeen reviewed intermediates/delegates for ADR-0005 bounded multigraphs.

Inactive constraint/dummy/label branches are checked explicitly. Port side,
ordering/cache, fixed-size placement, margins and bounds retain their real
source writes. The reviewed node-spacing def-use reduction is not a no-op.
"""
import math

from ..._errors import UnsupportedFeatureError
from .graph import Insets, Layer

_SIDE_ORDER = {"NORTH": 0, "EAST": 1, "SOUTH": 2, "WEST": 3}


def _outside(message):
    raise UnsupportedFeatureError("UNSUPPORTED_PROCESSOR_INPUT", "", message)


def _nodes(graph, *, e05=True):
    flags = graph.properties.get("GRAPH_PROPERTIES")
    flags = set() if flags is None else flags
    if (graph.properties.get("DIRECTION", "RIGHT") not in ("RIGHT", "LEFT", "DOWN", "UP") or not isinstance(flags, set)
            or not flags <= {"SELF_LOOPS"}):
        _outside("Direction transforms/advanced graph properties require another source slice")
    nodes = [*graph.layerless_nodes, *(node for layer in graph.layers for node in layer.nodes)]
    limit = 176 if e05 else 4
    if len(nodes) > limit or len({id(n) for n in nodes}) != len(nodes):
        _outside("The work representation exceeds the reviewed distinct-node bound")
    if e05 and (len(graph.layers) > 8 or sum(n.type == "NORMAL" for n in nodes) > 8):
        _outside("The reviewed work graph has at most eight original nodes and layers")
    total_ports = 0
    for node in nodes:
        if node.type not in (("NORMAL", "LONG_EDGE") if e05 else ("NORMAL",)) or node.graph is not graph:
            _outside("The node type or work graph ownership is unreviewed")
        if node.type == "LONG_EDGE" and (node.size.x != 0 or node.size.y != 1):
            _outside("Reviewed long-edge dummies retain the default thickness1")
        if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1_000_000
               for value in (node.size.x, node.size.y)):
            _outside("Given dimensions exceed the reviewed numeric domain")
        if node.properties.get("LAYER_CONSTRAINT", "NONE") != "NONE":
            _outside("Layer constraints require their full source branches")
        for port in node.ports:
            if port.owner is not node or port.origin is not None:
                _outside("Only correctly owned implicit ports are reviewed")
        total_ports += len(node.ports)
    if e05 and total_ports > 392:
        _outside("Work ports exceed the reviewed 28-edge split bound")
    return nodes


def edge_and_layer_constraint_edge_reverser(graph):
    remaining = []
    for node in _nodes(graph):
        if node.type != "NORMAL":
            _outside("Edge constraint preprocessing precedes dummy insertion")
        if node.properties.get("LAYER_CONSTRAINT", "NONE") == "NONE":
            remaining.append(node)
    for node in remaining:
        if node.properties.get("PORT_CONSTRAINTS", "FREE") not in ("FREE", "UNDEFINED"):
            _outside("Pre-layout fixed ports require the full reversal branch")
        # Both actual node passes execute. No layer constraint and free ports
        # guard out reverseEdges, rather than replacing the whole stage by pass.


def layer_constraint_preprocessor(graph):
    hidden = []
    for node in _nodes(graph):
        if node.type != "NORMAL":
            _outside("Layer preprocessing precedes dummy insertion")
        constraint = node.properties.get("LAYER_CONSTRAINT", "NONE")
        if constraint in ("FIRST_SEPARATE", "LAST_SEPARATE"):
            _outside("Hidden constrained nodes require a wider source slice")
    if hidden:
        graph.properties["HIDDEN_NODES"] = hidden


def layer_constraint_postprocessor(graph):
    if any(node.type != "NORMAL" for node in _nodes(graph)):
        _outside("Layer postprocessing precedes dummy insertion")
    if graph.layers:
        # The real source creates these temporary layers even when no node
        # constraint requests a move into them.
        first_labels, last_labels = Layer(graph), Layer(graph)
        for layer in list(graph.layers):
            for node in list(layer.nodes):
                if node.properties.get("LAYER_CONSTRAINT", "NONE") != "NONE":
                    _outside("First/last constraint node moves are not reviewed")
        if first_labels.nodes:
            graph.layers.insert(0, first_labels)
        if last_labels.nodes:
            graph.layers.append(last_labels)
        graph.layers[:] = [layer for layer in graph.layers if layer.nodes]
    if "HIDDEN_NODES" in graph.properties:
        _outside("Hidden node restoration is outside this slice")


def long_edge_splitter(graph):
    from .long_edges import long_edge_splitter as split
    split(graph)


def _set_side(port, side):
    port.side = side
    if side == "EAST":
        port.anchor.x, port.anchor.y = port.size.x, port.size.y / 2
    elif side == "WEST":
        port.anchor.x, port.anchor.y = 0.0, port.size.y / 2
    else:
        _outside("Only flow-side implicit ports are reviewed")


def _port_processor_nodes(graph, *, include_layerless):
    """Structural native graph checks; no old topology or shape-count domain."""
    nodes = list(graph.layerless_nodes) if include_layerless else []
    for layer in graph.layers:
        if layer.graph is not graph:
            _outside("Port processing requires actual layer ownership")
        nodes.extend(layer.nodes)
    if len({id(node) for node in nodes}) != len(nodes):
        _outside("Port processing requires distinct native nodes")
    ports = set()
    for node in nodes:
        if node.graph is not graph:
            _outside("Port processing requires actual node graph ownership")
        if node.properties.get("PORT_CONSTRAINTS", "UNDEFINED") not in {
                "UNDEFINED", "FREE", "FIXED_SIDE", "FIXED_ORDER", "FIXED_RATIO", "FIXED_POS"}:
            _outside("Unknown native port constraint")
        for port in node.ports:
            if id(port) in ports or port.owner is not node:
                _outside("Port processing requires distinct correctly owned native ports")
            ports.add(id(port))
    return nodes


def port_side_processor(graph):
    """E13-P05A actual source side traversal, including explicit/dummy ports."""
    from .ports import process_port_sides
    _port_processor_nodes(graph, include_layerless=True)
    process_port_sides(graph)


def port_list_sorter(graph):
    """E13-P05A uses the approved actual P02/P02S comparator/sort/cache path."""
    from .ports import sort_port_lists
    _port_processor_nodes(graph, include_layerless=False)
    strategy = graph.properties.get("PORT_SORTING_STRATEGY", "INPUT_ORDER")
    if strategy not in {"INPUT_ORDER", "PORT_DEGREE"}:
        _outside("Unknown native port sorting strategy")
    sort_port_lists(graph, strategy=strategy)


def _source_port_side_range(ports, side):
    """Worker findPortSideRange literal low/high and stale-low read."""
    if not ports:
        return 0, 0
    low, current = 0, ports[0].side
    lower, upper = _SIDE_ORDER[side], _SIDE_ORDER[side] + 1
    while low < len(ports) - 1 and _SIDE_ORDER[current] < lower:
        low += 1
        current = ports[low].side
    high = low
    while high < len(ports) - 1 and _SIDE_ORDER[current] < upper:
        high += 1
        current = ports[low].side
    return low, high


def in_layer_constraint_processor(graph):
    _nodes(graph)
    for layer in graph.layers:
        top_insertion, bottom = -1, []
        for index, node in enumerate(list(layer.nodes)):
            constraint = node.properties.get("IN_LAYER_CONSTRAINT", "NONE")
            if constraint != "NONE":
                _outside("TOP/BOTTOM reordering requires another source branch")
            if top_insertion == -1 and constraint != "TOP":
                top_insertion = index
        if bottom:
            _outside("Unexpected bottom-constrained nodes")


def label_and_node_size_processor(graph):
    nodes = _nodes(graph, e05=True)
    if graph.layerless_nodes:
        _outside("Node-size adapter visits prepared layers only")
    for node in nodes:
        if node.type != "NORMAL":
            continue  # Source LGraphAdapter's explicit NORMAL predicate.
        if (node.properties.get("NODE_SIZE_CONSTRAINTS")
                or node.properties.get("NODE_SIZE_OPTIONS", {"DEFAULT_MINIMUM_SIZE"}) != {"DEFAULT_MINIMUM_SIZE"}):
            _outside("The reviewed node-spacing def-use needs fixed given sizes")
        if node.properties.get("PORT_CONSTRAINTS") not in ("FIXED_SIDE", "FIXED_ORDER"):
            _outside("Side/order processing must precede node spacing")
        if len(node.ports) > 56:
            _outside("The reviewed 28-edge importer creates at most 56 ports on one node")
        if any(key in node.properties for key in ("PORT_ALIGNMENT_DEFAULT", "PORT_ALIGNMENT_EAST", "PORT_ALIGNMENT_WEST", "PORT_ALIGNMENT_NORTH", "PORT_ALIGNMENT_SOUTH", "SPACING_INDIVIDUAL", "NODE_LABELS_PLACEMENT", "PORT_LABELS_PLACEMENT", "NODE_LABELS_PADDING")):
            _outside("Explicit alignment/individual-spacing overrides are outside this cell proof")
        # Actual inherited type4 defaults are graph-owned mutable clones.
        # Core EnumSet defaults lack GWT type4: do not invent node properties.
        from .directions import get_node_labels_padding
        label_padding = get_node_labels_padding(graph)
        if any(getattr(label_padding, side) != 5 for side in ("top", "right", "bottom", "left")):
            _outside("Inherited label-padding default changed")
        for key, expected in (("SPACING_PORTS_SURROUNDING", 0),):
            value = graph.properties.get(key)
            if value is None:
                value = Insets(expected, expected, expected, expected)
                graph.properties[key] = value
            if not isinstance(value, Insets) or any(getattr(value, side) != expected for side in ("top", "right", "bottom", "left")):
                _outside("Inherited label/port-surrounding defaults changed")
        width, height = node.size.x, node.size.y
        for index, port in enumerate(node.ports):
            if port.side not in ("NORTH", "EAST", "WEST") or port.size.x != 0 or port.size.y != 0:
                _outside("Only reviewed zero-size implicit flow or default NORTH loop ports are admitted")
            if port.side == "NORTH" and (port.incoming_edges or port.outgoing_edges):
                _outside("Default loop edges stay detached during node sizing")
            if any(key in port.properties for key in ("PORT_BORDER_OFFSET", "PORT_ANCHOR")):
                _outside("Port border/anchor overrides require their full source branches")
            port.id = index  # Source createPortContexts sets volatile IDs per node.
        # The real process places horizontal ports before the vertical pass.
        # NORTH contexts sort by ascending volatile ID. SOUTH is empty under
        # the approved default NORTH/STACKED loop prefix. Container mode0 gives
        # the NORTH cell the given width despite nonzero scratch minima; empty
        # constraints keep the contribution flags false and do not resize it.
        north = [port for port in node.ports if port.side == "NORTH"]
        if north:
            calculated_width = 0.0
            for index, port in enumerate(north):
                calculated_width += 0.0 + port.size.x + 0.0
                if index + 1 < len(north):
                    calculated_width += 10.0
            calculated_width += 2 * 10.0
            available = width - 0.0 - 0.0
            current_x, spacing = 0.0 + 0.0, 10.0
            if len(north) == 1:
                calculated_width -= 2 * 10.0
                current_x += (available - calculated_width) / 2
            elif available < calculated_width:
                spacing += (available - calculated_width) / (len(north) + 1)
                current_x += spacing
            else:
                extra = (available - calculated_width) / (len(north) + 1)
                spacing += max(0.0, extra)
                current_x += spacing
            for port in north:
                port.pos.x = current_x + 0.0
                port.pos.y = -port.size.y
                current_x += 0.0 + port.size.x + 0.0 + spacing
        # NS5-G2 keeps full given cell height even when the noncontributing
        # DISTRIBUTED scratch minimum is nonzero. TreeMultimap's per-side
        # comparator uses ascending volatile IDs EAST and descending WEST.
        for side in ("EAST", "WEST"):
            ports = [port for port in node.ports if port.side == side]
            if side == "WEST":
                ports.reverse()
            count = len(ports)
            if count == 0:
                continue
            calculated_height = 0.0
            for index, port in enumerate(ports):
                calculated_height += 0.0 + port.size.y + 0.0
                if index + 1 < count:
                    calculated_height += 10.0
            calculated_height += 2 * 10.0  # Core DISTRIBUTED default.
            available = height - 0.0 - 0.0
            current_y = 0.0 + 0.0
            spacing = 10.0
            if count == 1:
                calculated_height -= 2 * 10.0
                current_y += (available - calculated_height) / 2
            elif available < calculated_height:
                spacing += (available - calculated_height) / (count + 1)
                current_y += spacing
            else:
                extra = (available - calculated_height) / (count + 1)
                spacing += max(0.0, extra)
                current_y += spacing
            for port in ports:
                port.pos.x = -port.size.x if side == "WEST" else width
                port.pos.y = current_y + 0.0
                # Preserve iterative source addition; h/(k+1) differs for
                # decimal and subnormal h and may erase a real tiny margin.
                current_y += 0.0 + port.size.y + 0.0 + spacing
        node.size.x, node.size.y = width, height  # Real fixed-size setSize write.
        # No COMPUTE_PADDING: source setNodePadding returns without a write.


def innermost_node_margin_calculator(graph):
    if graph.layerless_nodes:
        _outside("Margin adapter visits prepared layers only")
    for node in _nodes(graph, e05=True):
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (node.pos.x, node.pos.y)):
            _outside("Margin calculation requires finite actual node positions")
        left, top, width, height = node.pos.x, node.pos.y, node.size.x, node.size.y
        for port in node.ports:
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in (port.pos.x, port.pos.y, port.size.x, port.size.y)):
                _outside("Margin calculation requires finite actual port rectangles")
            x, y = port.pos.x + node.pos.x, port.pos.y + node.pos.y
            x1, y1 = min(left, x), min(top, y)
            x2, y2 = max(left + width, x + port.size.x), max(top + height, y + port.size.y)
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            left, top, width, height = x1, y1, x2 - x1, y2 - y1
        node.margin.top = max(0.0, node.pos.y - top)
        node.margin.bottom = max(0.0, top + height - (node.pos.y + node.size.y))
        node.margin.left = max(0.0, node.pos.x - left)
        node.margin.right = max(0.0, left + width - (node.pos.x + node.size.x))


def layer_size_and_graph_height_calculator(graph):
    for node in _nodes(graph):
        if any(type(v) not in (int, float) or not math.isfinite(v)
               for v in (node.pos.y, node.margin.top, node.margin.right, node.margin.bottom, node.margin.left)):
            _outside("Layer bounds require finite actual placement and margins")
    minimum_y, maximum_y, found = math.inf, -math.inf, False
    for layer in graph.layers:
        layer.size.x, layer.size.y = 0.0, 0.0
        if not layer.nodes:
            continue
        found = True
        for node in layer.nodes:
            layer.size.x = max(layer.size.x, node.size.x + node.margin.left + node.margin.right)
        first, last = layer.nodes[0], layer.nodes[-1]
        top = first.pos.y - first.margin.top
        bottom = last.pos.y + last.size.y + last.margin.bottom
        layer.size.y = bottom - top
        minimum_y, maximum_y = min(minimum_y, top), max(maximum_y, bottom)
    if not found:
        minimum_y, maximum_y = 0.0, 0.0
    graph.size.y = maximum_y - minimum_y
    graph.offset.y -= minimum_y


def long_edge_joiner(graph):
    from .long_edges import long_edge_joiner as join
    join(graph)


def end_label_sorter(graph):
    for node in _nodes(graph):
        if node.type != "NORMAL":
            _outside("Source long-edge joining must precede final end-label sorting")
        # Stream predicate selects NORMAL, then accept_73 really invokes
        # processNode_3. Its inner presence test guards sorting, not this scan.
        if "END_LABELS" in node.properties:
            _outside("End-label cell initialization/sorting is not admitted")


def reversed_edge_restorer(graph):
    """Restore source-reversed edges after real join/self-loop restoration."""
    from .cycles import restore_reversed_edges
    return restore_reversed_edges(graph)


def self_loop_pre_processor(graph):
    from .loops import self_loop_pre_processor as operation
    return operation(graph)


def self_loop_port_restorer(graph):
    from .loops import self_loop_port_restorer as operation
    return operation(graph)


def self_loop_router(graph):
    from .loops import self_loop_router as operation
    return operation(graph)


def self_loop_post_processor(graph):
    from .loops import self_loop_post_processor as operation
    return operation(graph)


INTERMEDIATE_PROCESSORS = {
    "SelfLoopPreProcessor": self_loop_pre_processor,
    "SelfLoopPortRestorer": self_loop_port_restorer,
    "SelfLoopRouter": self_loop_router,
    "SelfLoopPostProcessor": self_loop_post_processor,
    "EdgeAndLayerConstraintEdgeReverser": edge_and_layer_constraint_edge_reverser,
    "LayerConstraintPreprocessor": layer_constraint_preprocessor,
    "LayerConstraintPostprocessor": layer_constraint_postprocessor,
    "LongEdgeSplitter": long_edge_splitter,
    "PortSideProcessor": port_side_processor,
    "PortListSorter": port_list_sorter,
    "InLayerConstraintProcessor": in_layer_constraint_processor,
    "LabelAndNodeSizeProcessor": label_and_node_size_processor,
    "InnermostNodeMarginCalculator": innermost_node_margin_calculator,
    "LayerSizeAndGraphHeightCalculator": layer_size_and_graph_height_calculator,
    "LongEdgeJoiner": long_edge_joiner,
    "EndLabelSorter": end_label_sorter,
    "ReversedEdgeRestorer": reversed_edge_restorer,
}
