"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual neighbouring NS node counts."""
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
    from pyelk.algorithms.layered.ns_neighbor_crossings import NorthSouthEdgeNeighbouringNodeCrossingsCounter
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('ns-neighbor-crossings-probe.cjs'))
    graph = LGraph(None, None, None); layer = Layer(graph); graph.layers.append(layer)
    nodes, ports = {}, {}
    for name, kind in s['nodes']:
        node = nodes[name] = LNode(graph, type=kind); set_layer(node, layer)
    for name, owner, side in s['ports']:
        port = ports[name] = LPort(); set_port_owner(port, nodes[owner]); set_side(port, side)
    for dummy, origin in s['dummyOrigins']:
        nodes[dummy].properties['ORIGIN'] = ports[origin].owner
        nodes[dummy].ports[0].properties['ORIGIN'] = ports[origin]
    for p, n in s['portDummies']: ports[p].properties['PORT_DUMMY'] = nodes[n]
    for a, b in s['edges']:
        edge = LEdge(); set_source(edge, ports[a]); set_target(edge, ports[b])
    row = list(nodes.values()); counter = NorthSouthEdgeNeighbouringNodeCrossingsCounter(row); counts = []
    for a, b in s['queries']:
        counter.count_crossings(nodes[a], nodes[b])
        counts.append([counter.upper_lower_crossings, counter.lower_upper_crossings])
    actual = dict(counts=counts,
        positions=[[name, counter.port_positions[p]] for name, p in ports.items() if p in counter.port_positions],
        rowIdentity=counter.layer is row, layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Supplied actual typed dummy/origin objects: two-dummy first-port degree, literal NS/LONG, Normal PORT_DUMMY count, independent side-local slots and same-node nonzero branch; not NS layout preparation')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
