"""Compare new source calculator/resolver/base caller with supplied ranks.

Usage: python compare_barycenter_forster.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
Rank production, crossing counters, ModelOrder and full layout are separate.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, set_layer, set_port_owner, set_source, set_target
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.phases import JavaRandom
    from pyelk.algorithms.layered.forster_constraints import ForsterConstraintResolver
    from pyelk.algorithms.layered.barycenter_order import BarycenterHeuristic
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('barycenter-forster-probe.cjs'))
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']: continue
        graph = LGraph(None, None, None, properties={'IN_LAYER_SUCCESSOR_CONSTRAINTS_BETWEEN_NON_DUMMIES': s.get('twoPass', False), 'CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER': False})
        layers = [Layer(graph, id=i) for i in range(s['layerCount'])]; graph.layers.extend(layers)
        nodes, by_node, ports, ranks, names = [], {}, {}, {}, {}
        for spec in s['nodes']:
            node = LNode(graph, id=len(layers[spec['layer']].nodes), type=spec.get('type', 'NORMAL'))
            names[id(node)] = spec['id']; nodes.append(node); by_node[spec['id']] = node; set_layer(node, layers[spec['layer']])
            for item in spec['ports']:
                port = LPort(id=len(ports)); set_port_owner(port, node); set_side(port, item['side'])
                ports[item['id']] = port; ranks[port] = item.get('rank', 0)
        for spec in s['nodes']:
            node = by_node[spec['id']]
            for dto, key in [('associates', 'BARYCENTER_ASSOCIATES'), ('successors', 'IN_LAYER_SUCCESSOR_CONSTRAINTS')]:
                if dto in spec: node.properties[key] = [by_node[name] for name in spec[dto]]
            if 'unit' in spec: node.properties['IN_LAYER_LAYOUT_UNIT'] = by_node[spec['unit']]
        for spec in s['edges']:
            edge = LEdge(); set_source(edge, ports[spec['source']]); set_target(edge, ports[spec['target']])
        resolver = ForsterConstraintResolver([list(layer.nodes) for layer in layers])
        refs = {node: resolver.states[node] for node in nodes}
        random = JavaRandom(s['seed'])
        heuristic = BarycenterHeuristic(resolver, random, SimpleNamespace(port_ranks=ranks)); heuristic.init_after_traversal()
        for spec in s['nodes']:
            if 'initialState' in spec:
                st = resolver.states[by_node[spec['id']]]; initial = spec['initialState']
                st.barycenter = initial['barycenter']; st.degree = initial['degree']; st.summed_weight = initial['weight']
        work = [by_node[name] for name in s['work']]
        if s['operation'] == 'calculate': heuristic.calculator.calculate_all(work, s['forward'])
        elif s['operation'] == 'resolve': resolver.process_constraints(work)
        else: heuristic.minimize_layer(work, s['preOrdered'], False, s['forward'])
        value = dict(order=[names[id(node)] for node in work],
                     states=[dict(id=names[id(node)], degree=resolver.states[node].degree, summedWeight=resolver.states[node].summed_weight,
                                  barycenter=resolver.states[node].barycenter, visited=resolver.states[node].visited,
                                  identityPreserved=resolver.states[node] is refs[node]) for node in nodes],
                     sharedState=heuristic.states is resolver.states, sharedRanks=heuristic.port_ranks is ranks,
                     nextRandom=random.next_double(), rankProducerExecuted=False, fullLayoutValidated=False)
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    assert rows and (not selected or len(rows) == 1)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullLayoutValidated=False, rankProducerExecuted=False,
                  scope='Only new calculator/resolver/base caller using supplied intermediate states and port ranks; no full crossing or layout')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
