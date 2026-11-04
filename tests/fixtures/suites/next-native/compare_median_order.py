"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual Median two-method path."""
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
    from pyelk.algorithms.layered.median_order import MedianHeuristic
    from pyelk.execution.entropy import random_unit
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('median-order-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes = {name: LNode(graph) for name in s['nodes']}
    order = []
    for index, names in enumerate(s['layers']):
        layer = Layer(graph, id=index)
        graph.layers.append(layer)
        for name in names:
            set_layer(nodes[name], layer)
        order.append([nodes[name] for name in names])
    for a, b in s['edges']:
        p, q, edge = LPort(), LPort(), LEdge()
        set_port_owner(p, nodes[a]); set_side(p, 'EAST')
        set_port_owner(q, nodes[b]); set_side(q, 'WEST')
        set_source(edge, p); set_target(edge, q)
    rng = JavaRandom(s['seed'])
    seed_before = [rng.seedhi, rng.seedlo]
    host_draws = []
    def host_random():
        host_draws.append(True)
        return random_unit()
    heuristic = MedianHeuristic(rng, host_random=host_random)
    seed_constructor = [rng.seedhi, rng.seedlo]
    missing_self = heuristic.compare(nodes['isolated'], nodes['isolated'])
    missing_pair = heuristic.compare(nodes['u'], nodes['v'])
    rows = list(order)
    names = {node: name for name, node in nodes.items()}
    view = lambda: [[names[node] for node in row] for row in order]
    weights = lambda: [node.properties.get('WEIGHT') for node in nodes.values()]
    first_result = heuristic.set_first_layer_order(order, True)
    after_first, first_weights = view(), weights()
    second_result = heuristic.minimize_crossings(order, 1, True, False)
    actual = dict(hostDraws=len(host_draws), seedBefore=seed_before,
        seedAfterConstructor=seed_constructor, seedAfter=[rng.seedhi, rng.seedlo],
        missingSelf=missing_self, missingPair=missing_pair, firstResult=first_result,
        secondResult=second_result, afterFirst=after_first, firstWeights=first_weights,
        order=view(), weights=weights(), sameRows=all(a is b for a, b in zip(rows, order)),
        deterministic=heuristic.is_deterministic(), alwaysImproves=heuristic.always_improves(),
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
        scope='Actual Median constructor host-draw count, separate seeded RNG, first-layer ranks, repeated adjacency/upper median, isolated positive-MAX mean, same row writes and asymmetric missing comparator')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
