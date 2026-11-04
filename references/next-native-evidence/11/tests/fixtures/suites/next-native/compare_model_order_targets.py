"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: target-chain source object witness."""
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
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge,
        set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.model_order_targets import long_edge_target_node_preprocessing
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('model-order-targets-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes = {name: LNode(graph, type=kind) for name, kind in s['nodes']}
    ports = {}
    for name, owner in s['ports']:
        port = ports[name] = LPort()
        set_port_owner(port, nodes[owner])
        set_side(port, 'EAST')
    def edge(a, b, order, reversed=False):
        e = LEdge()
        set_source(e, ports[a])
        set_target(e, ports[b])
        if order is not None:
            e.properties['MODEL_ORDER'] = order
        if reversed:
            e.properties['REVERSED'] = True
        return e
    for args in s['edges']:
        edge(*args)
    node, port = s['explicitTarget']
    nodes[node].properties['LONG_EDGE_TARGET'] = ports[port]
    for port, node in s['oldPortTargets']:
        ports[port].properties['LONG_EDGE_TARGET_NODE'] = nodes[node]
    values = long_edge_target_node_preprocessing(nodes[s['source']])
    boxes = [values[nodes[name]] for name in s['targets']]
    memo_same = values is long_edge_target_node_preprocessing(nodes[s['source']])
    names = {node: name for name, node in nodes.items()}
    port_targets = [[name, 'LONG_EDGE_TARGET_NODE' in ports[name].properties,
        names.get(ports[name].properties.get('LONG_EDGE_TARGET_NODE'))] for name in s['queryPorts']]
    empty = long_edge_target_node_preprocessing(nodes['cached'])
    edge(*s['lateEdge'])
    again = long_edge_target_node_preprocessing(nodes['cached'])
    actual = dict(targetValues=[box.value for box in boxes], targetBoxesSame=boxes[0] is boxes[1],
        memoSame=memo_same, portTargets=port_targets, lateMemoSame=empty is again,
        lateTargetAbsent='LONG_EDGE_TARGET_NODE' not in ports['cachep'].properties,
        lateMapEmpty=not any(nodes[name] in again for name in s['targets']), layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Target chain, first physical branch, reversed skip, null removal, fresh boxed minima and cached empty map; no geometry or complete importer')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
