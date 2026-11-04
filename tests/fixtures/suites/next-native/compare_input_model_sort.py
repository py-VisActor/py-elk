"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: real two-pass model-input sort."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered import input_model_sort as phase
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('input-model-sort-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes, ports = {}, {}
    for item in s['nodes']:
        node = nodes[item['id']] = LNode(graph)
        node.properties.update(MODEL_ORDER=item['order'], PORT_CONSTRAINTS=item['constraint'])
        node.labels = [SimpleNamespace(text=item['id'])]
        for name, order in item['ports']:
            port = ports[name] = LPort()
            set_port_owner(port, node)
            set_side(port, item['side'])
            port.properties['MODEL_ORDER'] = order
            port.labels = [SimpleNamespace(text=name)]
    for index, names in enumerate(s['layers']):
        layer = Layer(graph, id=20 + index)
        graph.layers.append(layer)
        for name in names:
            set_layer(nodes[name], layer)
    for a, b, order in s['edges']:
        edge = LEdge()
        set_source(edge, ports[a])
        set_target(edge, ports[b])
        edge.properties['MODEL_ORDER'] = order
    graph.properties.update(MAX_MODEL_ORDER_NODES=len(nodes),
        CONSIDER_MODEL_ORDER_STRATEGY='PREFER_NODES', CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER=True)
    node_ids = {node: name for name, node in nodes.items()}
    port_ids = {port: name for name, port in ports.items()}
    events = []
    class Monitor:
        def begin(self, name, total):
            events.append(dict(kind='begin', name=name, total=total))
        def log(self, text):
            events.append(dict(kind='log', text=text))
        def done(self):
            events.append(dict(kind='done'))
    saved = phase.insertion_sort
    def traced(row, comparator):
        big, small = comparator.bigger_than, comparator.smaller_than
        old = [node_ids[n] for n in row]
        previous = [node_ids[n] for n in comparator.previous_layer]
        saved(row, comparator)
        events.append(dict(kind='insertion', beforePorts=comparator.before_ports,
            before=old, previous=previous, after=[node_ids[n] for n in row],
            newCaches=comparator.bigger_than is not big and comparator.smaller_than is not small,
            cacheSizes=[len(comparator.bigger_than), len(comparator.smaller_than)]))
    phase.insertion_sort = traced
    try:
        phase.sort_by_input_model(graph, Monitor())
    finally:
        phase.insertion_sort = saved
    actual = dict(events=events,
        layers=[dict(id=layer.id, nodes=[node_ids[n] for n in layer.nodes]) for layer in graph.layers],
        ports=[dict(id=item['id'], ports=[port_ids[p] for p in nodes[item['id']].ports]) for item in s['nodes']],
        layoutExecuted=False, workingGraphPhaseExecuted=True, suppliedInternalModelOrder=True)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual,
        expected=original['observation'], comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, workingGraphPhaseExecuted=True, fullValidation=False,
        scope='Supplied internal model order: actual two insertion passes, fresh previous-layer snapshots/cache replacement, fixed-ratio sorting vs fixed-order/position skips, real edge-target port sorting and eager diagnostic log strings')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
