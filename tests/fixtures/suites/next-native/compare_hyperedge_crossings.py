"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual shared-port bundle counter."""
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
    from pyelk.algorithms.layered.hyperedge_crossings import HyperedgeCrossingsCounter
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('hyperedge-crossings-probe.cjs'))
    rows = []
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        graph = LGraph(None, None, None); nodes = {}; ports = {}; names = {}; edges = []
        for item in case['nodes']:
            node = LNode(graph); nodes[item['id']] = node
            for name, side in item['ports']:
                port = LPort(id=len(ports)); set_port_owner(port, node); set_side(port, side)
                ports[name] = port; names[port] = name
        order = []
        for li, ids in enumerate(case['layers']):
            layer = Layer(graph, id=li); graph.layers.append(layer); node_order = []
            for ni, name in enumerate(ids):
                node = nodes[name]; node.id = ni; set_layer(node, layer); node_order.append(node)
            order.append(node_order)
        for a, b in case['edges']:
            edge = LEdge(); set_source(edge, ports[a]); set_target(edge, ports[b]); edges.append(edge)
        positions = {port: 17 for port in ports.values()}
        counter = HyperedgeCrossingsCounter(positions)
        original_build = counter._build_hyperedges
        observed = []
        def delegate(left, right):
            result = original_build(left, right)
            observed.extend(result[0])
            return result
        counter._build_hyperedges = delegate
        try:
            count = counter.count_crossings(*order)
        finally:
            counter._build_hyperedges = original_build
        actual = dict(count=count,
            positions=[dict(id=name, value=positions[port]) for name, port in ports.items()],
            positionBufferShared=counter.port_positions is positions,
            bundles=[dict(ports=[names[p] for p in he.ports], edges=[edges.index(e) for e in he.edges],
                bounds=[he.upper_left, he.lower_left, he.upper_right, he.lower_right]) for he in observed],
            observerDelegated=True, layoutExecuted=False)
        rows.append(dict(id=case['id'], actual=actual, expected=expected['value'],
            differences=diff(expected['value'], actual)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows,
        sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Prepared adjacent layered objects, actual bundle union/order/positions and full inversion-plus-corner score only; no dispatcher or full crossing sweep')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
