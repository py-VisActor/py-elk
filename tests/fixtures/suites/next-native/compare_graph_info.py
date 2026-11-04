"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual GraphInfo initialization only."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5]); source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.phases import JavaRandom
    from pyelk.algorithms.layered.graph_info import GraphInfoHolder, get_graph_properties
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes()); original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('graph-info-probe.cjs'))
    assert original['sourceFacts']['defaultCloneable'] is False
    graph = LGraph(None, None, None); other = LGraph(None, None, None); nested = LGraph(None, None, None)
    default = get_graph_properties(graph); other_default = get_graph_properties(other)
    shared = default is other_default; default.add('EXTERNAL_PORTS')
    mutation = 'EXTERNAL_PORTS' in get_graph_properties(other)
    nodes = {}; ports = {}
    for item in s['nodes']:
        node = LNode(graph); nodes[item['id']] = node
        if item['id'] in s['nested']: node.nested_graph = nested
        for name, side in item['ports']:
            port = LPort(); set_port_owner(port, node); set_side(port, side); ports[name] = port
    layers = []
    for ids in s['layers']:
        layer = Layer(graph); graph.layers.append(layer); layers.append(layer)
        for name in ids: set_layer(nodes[name], layer)
    for a, b in s['edges']:
        edge = LEdge(); set_source(edge, ports[a]); set_target(edge, ports[b])
    rng = JavaRandom(s['seed']); graph.random = rng; bits = []; real_next = rng.next
    def record_next(count):
        bits.append(count); return real_next(count)
    rng.next = record_next
    try:
        info = GraphInfoHolder(graph, 'BARYCENTER', [])
    finally:
        rng.next = real_next
    heuristic = info.cross_minimizer.heuristic; resolver = heuristic.constraint_resolver; marker = object()
    info.set_best_node_and_port_order(marker); info.set_currently_best_node_and_port_order(marker)
    names = {node: name for name, node in nodes.items()}
    actual = dict(defaultShared=shared, defaultMutationVisible=mutation,
        defaultAbsent='GRAPH_PROPERTIES' not in graph.properties and 'GRAPH_PROPERTIES' not in other.properties,
        hasExternalPorts=info.has_external_ports, hasParent=info.has_parent, parentNull=info.parent_graph_data is None,
        useBottomUp=info.use_bottom_up,
        ownedRows=all(row is not layers[i].nodes and all(n is layers[i].nodes[j] for j, n in enumerate(row)) for i, row in enumerate(info.current_node_order)),
        nodeIds=[[n.id for n in row] for row in info.current_node_order], layerIds=[layer.id for layer in layers],
        portIds=[port.id for port in ports.values()], ports=info.n_ports,
        childGraphs=[g is nested for g in info.child_graphs], distributor=type(info.port_distributor).__name__,
        randomBits=bits, randomState=[rng.seedhi, rng.seedlo], minimizer=type(heuristic).__name__,
        liveStates=heuristic.states is resolver.states, liveRanks=heuristic.port_ranks is info.port_distributor.port_ranks,
        nodePositions=[list(row) for row in info.port_distributor.node_positions],
        portRanks=[info.port_distributor.port_ranks[port] for port in ports.values()],
        states=[dict(id=names[node], degree=resolver.states[node].degree, weight=resolver.states[node].summed_weight,
            barycenter=resolver.states[node].barycenter) for row in info.current_node_order for node in row],
        separateInfoBuffer=info.port_positions is not info.crossings_counter.crossing_counter.port_positions,
        sharedChildBuffer=info.crossings_counter.crossing_counter.port_positions is info.crossings_counter.hyperedge_crossings_counter.port_positions,
        snapshotAssignmentsKeepReference=info.best_node_and_port_order is marker and info.currently_best_node_and_port_order is marker,
        layoutExecuted=False)
    default.remove('EXTERNAL_PORTS')
    comparison = diff(original['observation'], actual)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        sourceOnlyFacts=original['sourceFacts'], layoutExecuted=False, fullValidation=False,
        scope='New Barycenter GraphInfo construction, one real factory/traversal, shared live state/ranks, enum default presence and reference setters only; no sweep optimization or forced-box parse claim')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
