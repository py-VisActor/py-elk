# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Dispatch of the reviewed elkjs 0.12.1 generated-worker default chain.
# Source commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source order: references/layered-default-path.json; component approvals:
# references/e06-component-approvals.json. See pyelk/_licenses/NOTICE-E06.md.
"""Real source-reviewed dispatch; traces observe work and never choose layout."""
import math

from .graph import Insets, LEdge, LNode, LPort, Layer, Vec2
from .scope import validate_slice

PROCESSOR_SEQUENCE = (
    "EdgeAndLayerConstraintEdgeReverser", "GreedyCycleBreaker", "LayerConstraintPreprocessor",
    "NetworkSimplexLayerer", "LayerConstraintPostprocessor", "LongEdgeSplitter", "PortSideProcessor",
    "PortListSorter", "LayerSweepCrossingMinimizer", "LayerSweepCrossingMinimizer",
    "InLayerConstraintProcessor", "LabelAndNodeSizeProcessor", "InnermostNodeMarginCalculator",
    "BKNodePlacer", "LayerSizeAndGraphHeightCalculator", "OrthogonalEdgeRouter", "LongEdgeJoiner",
    "EndLabelSorter", "ReversedEdgeRestorer",
)

# Source configurations are selected once, before late NORTH loop ports exist.
SELF_LOOP_PROCESSOR_SEQUENCE = (
    "EdgeAndLayerConstraintEdgeReverser", "SelfLoopPreProcessor", "GreedyCycleBreaker",
    "LayerConstraintPreprocessor", "NetworkSimplexLayerer", "LayerConstraintPostprocessor",
    "LongEdgeSplitter", "PortSideProcessor", "PortListSorter", "LayerSweepCrossingMinimizer",
    "LayerSweepCrossingMinimizer", "SelfLoopPortRestorer", "InLayerConstraintProcessor",
    "LabelAndNodeSizeProcessor", "InnermostNodeMarginCalculator", "SelfLoopRouter", "BKNodePlacer",
    "LayerSizeAndGraphHeightCalculator", "OrthogonalEdgeRouter", "LongEdgeJoiner", "SelfLoopPostProcessor",
    "EndLabelSorter", "ReversedEdgeRestorer",
)


def _trace_identity(value, identities):
    group = "node" if isinstance(value, LNode) else "port" if isinstance(value, LPort) else "edge"
    registry = identities.setdefault(group, {})
    if value not in registry:
        registry[value] = group + ":" + str(len(registry))
    return registry[value]


def _node_name(node, identities=None):
    return (node.origin.id if node.origin is not None else
            "temporary:" + (_trace_identity(node, identities) if identities is not None else str(node.id)))


def _trace_value(value, identities=None):
    if value is None or type(value) in (str, int, float, bool):
        if type(value) is float and not math.isfinite(value):
            return {"internalNonfinite": "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"}
        return value
    if isinstance(value, Vec2):
        return {"x": value.x, "y": value.y}
    if isinstance(value, Insets):
        return {side: getattr(value, side) for side in ("top", "right", "bottom", "left")}
    if isinstance(value, LNode):
        result = {"node": _node_name(value, identities)}
        if identities is not None:
            result["traceId"] = _trace_identity(value, identities)
        return result
    if isinstance(value, LPort):
        result = {"port": value.id, "node": _node_name(value.owner, identities) if value.owner else None}
        if identities is not None:
            result["traceId"] = _trace_identity(value, identities)
        return result
    if isinstance(value, LEdge):
        result = {"edge": value.origin.id if value.origin else value.id}
        if identities is not None:
            result["traceId"] = _trace_identity(value, identities)
        return result
    if isinstance(value, Layer):
        return {"layer": value.id}
    if isinstance(value, dict):
        return {key if type(key) is str else str(_trace_value(key, identities)): _trace_value(child, identities)
                for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_trace_value(child, identities) for child in value]
    if isinstance(value, (set, frozenset)):
        return {"setValues": sorted((_trace_value(child, identities) for child in value), key=str)}
    from .loops import SelfLoopHolder, snapshot_holder
    if isinstance(value, SelfLoopHolder):
        return snapshot_holder(value, lambda child: _trace_value(child, identities))
    # Development-only markers for other support objects; never repr addresses.
    return {"supportType": type(value).__name__}


def snapshot(graph, *, identities=None):
    identities = {} if identities is None else identities
    value = lambda child: _trace_value(child, identities)
    name = lambda node: _node_name(node, identities)
    identity = lambda child: _trace_identity(child, identities)
    nodes, seen = [], set()
    for node in [*graph.layerless_nodes, *(node for layer in graph.layers for node in layer.nodes)]:
        if id(node) not in seen:
            nodes.append(node)
            seen.add(id(node))
    edges = []
    for node in nodes:
        identity(node)
        for port in node.ports:
            identity(port)
            for edge in [*port.incoming_edges, *port.outgoing_edges]:
                if edge not in edges:
                    edges.append(edge)
                    identity(edge)
    return {"layerless": [name(node) for node in graph.layerless_nodes],
            "layers": [{"id": layer.id, "nodes": [name(node) for node in layer.nodes], "size": value(layer.size)}
                       for layer in graph.layers],
            "nodes": [{"originId": name(node), "traceId": identity(node), "id": node.id, "type": node.type,
                       "pos": value(node.pos), "size": value(node.size), "margin": value(node.margin),
                       "properties": value(node.properties), "portSidesCached": node.port_sides_cached,
                       "selfLoopHolder": value(node.properties.get("SELF_LOOP_HOLDER")),
                       "portSideIndices": value(node.port_side_indices),
                       "ports": [{"id": port.id, "side": port.side, "pos": _trace_value(port.pos),
                                  "traceId": identity(port), "size": value(port.size), "anchor": value(port.anchor),
                                  "incoming": [edge.origin.id if edge.origin else edge.id for edge in port.incoming_edges],
                                  "outgoing": [edge.origin.id if edge.origin else edge.id for edge in port.outgoing_edges],
                                  "incomingTraceIds": [identity(edge) for edge in port.incoming_edges],
                                  "outgoingTraceIds": [identity(edge) for edge in port.outgoing_edges]}
                                 for port in node.ports]} for node in nodes],
            "edges": [{"traceId": identity(edge), "originId": edge.origin.id if edge.origin else None,
                       "id": edge.id, "source": value(edge.source), "target": value(edge.target),
                       "bendPoints": [value(point) for point in edge.bend_points], "properties": value(edge.properties)}
                      for edge in edges],
            "size": value(graph.size), "offset": value(graph.offset), "padding": value(graph.padding),
            "random": None if graph.random is None else {"state48": graph.random.state48, "primitiveDraws": graph.random.primitive_draws}}


def layout_context(context, *, trace=None, monitor=None):
    from .components import combine_components, finish_component, resize_graph, split_components
    from .directions import direction_postprocessor, direction_preprocessor
    from .import_export import export_layout, import_raw_graph
    from .phases import (JavaRandom, bk_node_placer, greedy_cycle_breaker, layer_sweep,
                         network_simplex_layerer, orthogonal_edge_router)
    from .processors import INTERMEDIATE_PROCESSORS

    admitted = validate_slice(context)
    if monitor is not None:
        monitor.begin('Recursive Graph Layout', admitted.node_count)
    work = import_raw_graph(context, None if admitted.node_count == 0 else JavaRandom(context.seed))
    if admitted.node_count == 0:
        if monitor is not None:
            monitor.done()
        return export_layout(work, finish=False)
    layered_monitor = None if monitor is None else monitor.sub_task(admitted.node_count)
    if layered_monitor is not None:
        layered_monitor.begin('Layered layout', 1)
    sequence = SELF_LOOP_PROCESSOR_SEQUENCE if "SELF_LOOPS" in work.properties["GRAPH_PROPERTIES"] else PROCESSOR_SEQUENCE
    if work.properties["DIRECTION"] != "RIGHT":
        sequence = ("GraphTransformer:PRE", *sequence, "GraphTransformer:POST")
    # Source prepare runs once. These are reviewed host representations of
    # shared RANDOM, SPACINGS and the configured ordered processor instances.
    work.properties.update(RANDOM=work.random, SPACINGS=work.options, PROCESSORS=sequence)
    expected_intermediates = set(SELF_LOOP_PROCESSOR_SEQUENCE) - {
        "GreedyCycleBreaker", "NetworkSimplexLayerer", "LayerSweepCrossingMinimizer", "BKNodePlacer", "OrthogonalEdgeRouter"}
    if set(INTERMEDIATE_PROCESSORS) != expected_intermediates:
        raise RuntimeError("Intermediate registry differs from reviewed default chain")
    main = {"GreedyCycleBreaker": greedy_cycle_breaker, "NetworkSimplexLayerer": network_simplex_layerer,
            "BKNodePlacer": bk_node_placer, "OrthogonalEdgeRouter": orthogonal_edge_router,
            "GraphTransformer:PRE": direction_preprocessor, "GraphTransformer:POST": direction_postprocessor}
    components = split_components(work)
    trace_identities = {}
    for component_index, component in enumerate(components):
        component_monitor = layered_monitor
        if layered_monitor is not None:
            from ...execution.diagnostics import log_modules, phase_name
            if len(components) != 1:
                component_monitor = layered_monitor.sub_task(1 / len(components))
                component_monitor.begin('Component Layout', 1)
            log_modules(component_monitor, component.properties['PROCESSORS'])
        sweep = 0
        for phase_index, name in enumerate(component.properties["PROCESSORS"]):
            strategy = None
            if name == "LayerSweepCrossingMinimizer":
                strategy = ("BARYCENTER", "TWO_SIDED_GREEDY_SWITCH")[sweep]
                sweep += 1
                operation = lambda graph, mode=strategy: layer_sweep(graph, strategy=mode)
            else:
                operation = main[name] if name in main else INTERMEDIATE_PROCESSORS[name]
            entry = None
            if trace is not None:
                entry = {"index": len(trace), "componentIndex": component_index,
                         "componentPhaseIndex": phase_index, "processor": name,
                         "strategy": strategy, "before": snapshot(component, identities=trace_identities)}
                trace.append(entry)
            try:
                phase_monitor = None
                if component_monitor is not None:
                    phase_monitor = component_monitor.sub_task(1 / len(component.properties['PROCESSORS']))
                    phase_monitor.begin(phase_name(name, strategy), 1)
                if phase_monitor is not None and name in ('NetworkSimplexLayerer', 'BKNodePlacer'):
                    operation(component, monitor=phase_monitor)
                else:
                    operation(component)
                if phase_monitor is not None:
                    phase_monitor.done()
            except Exception as error:
                if entry is not None:
                    entry.update(outcome="threw", error={"type": type(error).__name__, "message": str(error)})
                raise
            if entry is not None:
                entry.update(outcome="returned", after=snapshot(component, identities=trace_identities))
        finish_component(component)
        if component_monitor is not None and component_monitor is not layered_monitor:
            component_monitor.done()
    combine_components(components, work)
    resize_graph(work)
    if layered_monitor is not None:
        layered_monitor.done()
    result = export_layout(work, finish=False)
    if monitor is not None:
        monitor.done()
    return result
