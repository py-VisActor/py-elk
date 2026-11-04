"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual lazy adjacency counter."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.two_node_crossings import BetweenLayerEdgeTwoNodeCrossingsCounter
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('two-node-crossings-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes, ports, order = {}, {}, []
    for name, ps in s['nodes']:
        node = nodes[name] = LNode(graph)
        for pid, side in ps:
            port = ports[pid] = LPort()
            set_port_owner(port, node); set_side(port, side)
    for index, names in enumerate(s['layers']):
        layer = Layer(graph, id=index); graph.layers.append(layer)
        for name in names: set_layer(nodes[name], layer)
        order.append([nodes[name] for name in names])
    def edge(a, b):
        e = LEdge(); set_source(e, ports[a]); set_target(e, ports[b])
    for args in s['edges']: edge(*args)
    counter = BetweenLayerEdgeTwoNodeCrossingsCounter(order, s['freeLayer'])
    def state(values):
        result = []
        for name in s['layers'][s['freeLayer']]:
            if nodes[name] not in values:
                result.append(dict(id=name, present=False)); continue
            a = values[nodes[name]]
            result.append(dict(id=name, present=True, size=a.size, currentSize=a.current_size,
                index=a.current_index, entries=[[x.position, x.cardinality, x.current_cardinality] for x in a.adjacency_list]))
        return result
    events, saved, cache_identity = [], None, True
    for index, (side, a, b) in enumerate(s['queries']):
        method = counter.count_both_side_crossings if side == 'BOTH' else counter.count_eastern_edge_crossings
        method(nodes[a], nodes[b])
        events.append(dict(counts=[counter.upper_lower_crossings, counter.lower_upper_crossings],
            east=state(counter.eastern_adjacencies), west=state(counter.western_adjacencies)))
        if index == s['lateEdgeAfter']:
            saved = counter.eastern_adjacencies[nodes['w']]
            edge(*s['lateEdge'])
        elif saved is not None:
            cache_identity = cache_identity and saved is counter.eastern_adjacencies[nodes['w']]
    actual = dict(positions=[[name, counter.port_positions[p]] for name, p in ports.items() if p in counter.port_positions],
        events=events, cacheIdentity=cache_identity, orderIdentity=counter.current_node_order is order,
        layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Real both-side cursor merge with duplicate/nonconsecutive runs, lazy whole-row capture, retained stale third node after edge addition, same-node early exit and same order identity')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
