"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: real feedback and recursive caches."""
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
    from pyelk.algorithms.layered.model_order_nodes import ModelOrderNodeComparator
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('model-order-feedback-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes, ports = {}, {}
    for name, kind, order in s['nodes']:
        node = nodes[name] = LNode(graph, type=kind)
        if order is not None:
            node.properties['MODEL_ORDER'] = order
    for name, owner, side in s['ports']:
        port = ports[name] = LPort()
        set_port_owner(port, nodes[owner])
        set_side(port, side)
    layers = []
    for index, names in enumerate(s['layers']):
        layer = Layer(graph, id=index)
        graph.layers.append(layer)
        for name in names:
            set_layer(nodes[name], layer)
        layers.append([nodes[name] for name in names])
    for a, b, order in s['edges']:
        edge = LEdge()
        set_source(edge, ports[a])
        set_target(edge, ports[b])
        edge.properties['MODEL_ORDER'] = order
    graph.properties['MAX_MODEL_ORDER_NODES'] = len(nodes)
    comparator = ModelOrderNodeComparator(graph, layers[0], 'PREFER_EDGES', before_ports=True)
    results = [comparator.compare(nodes[a], nodes[b]) for a, b in s['cyclicQueries']]
    def relation(c, name):
        values = getattr(c, name)
        return [dict(id=a, present=node in values,
            members=[b for b, other in nodes.items() if other in values.get(node, ())]) for a, node in nodes.items()]
    recursive = ModelOrderNodeComparator(graph, layers[0], 'PREFER_EDGES')
    a, b = s['recursiveQuery']
    recursive_result = recursive.compare(nodes[a], nodes[b])
    actual = dict(results=results, bigger=relation(comparator, 'bigger_than'),
        smaller=relation(comparator, 'smaller_than'), recursiveResult=recursive_result,
        recursiveBigger=relation(recursive, 'bigger_than'), recursiveSmaller=relation(recursive, 'smaller_than'),
        layoutExecuted=False, suppliedInternalModelOrder=True)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Real shared-port feedback performs opposite inner/outer updates and cyclic caches; separate recursive continuation resumes and updates caller; membership projected in input order only')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
