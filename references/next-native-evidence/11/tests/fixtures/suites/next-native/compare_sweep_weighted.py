"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: weighted NONE read-order leaf."""
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
    from pyelk.algorithms.layered.phases import JavaRandom
    from pyelk.algorithms.layered.layer_sweep import LayerSweepCrossingMinimizer
    from pyelk.algorithms.layered.graph_info import GraphInfoHolder
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('sweep-weighted-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes, ports = {}, {}
    for item in s['nodes']:
        node = LNode(graph)
        port = LPort()
        nodes[item['id']] = node
        ports[item['port']] = port
        set_port_owner(port, node)
        set_side(port, item['side'])
    for names in s['layers']:
        layer = Layer(graph)
        graph.layers.append(layer)
        for name in names: set_layer(nodes[name], layer)
    for a, b in s['edges']:
        edge = LEdge()
        set_source(edge, ports[a])
        set_target(edge, ports[b])
    graph.random = JavaRandom(s['seed'])
    graph.properties.update(CONSIDER_MODEL_ORDER_STRATEGY='NONE',
        CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE=s['nodeInfluence'],
        CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE=s['portInfluence'])
    controller = LayerSweepCrossingMinimizer('BARYCENTER')
    data = GraphInfoHolder(graph, 'BARYCENTER', [])
    controller.graph_info_holders = [data]
    tracked = dict(CONSIDER_MODEL_ORDER_STRATEGY='strategy',
        CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY='group',
        CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE='node',
        CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE='port')
    events = []
    class ObservedProperties(dict):
        def get(self, key, default=None):
            if key in tracked: events.append('read:' + tracked[key])
            return super().get(key, default)
    graph.properties = ObservedProperties(graph.properties)
    counter = data.crossings_counter.crossing_counter
    absent = getattr(counter, 'index_tree', None) is None
    real = data.crossings_counter.count_all_crossings
    def count(order):
        events.append('all')
        return real(order)
    data.crossings_counter.count_all_crossings = count
    score = controller.count_current_number_of_crossings(data, weighted=True)
    actual = dict(score=score, events=events, beforeTreeAbsent=absent,
        afterTreePresent=getattr(counter, 'index_tree', None) is not None,
        positions=[counter.port_positions[p] for p in ports.values()], layoutExecuted=False)
    comparison = diff(original['observation'], actual)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Only new weighted NONE score with four real property reads before actual AllCounter/scratch materialization; no fake model-order cost and no full phase replay')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
