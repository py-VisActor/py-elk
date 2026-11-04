"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT [CASE_ID]: TypeDecider objects."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected_case = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.sweep_type import LayerSweepTypeDecider
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    expected = json.loads(oracle.read_bytes())
    spec = json.loads(request.read_bytes())
    assert expected['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert expected['requestSha256'] == sha(request)
    assert expected['probeSha256'] == sha(request.with_name('sweep-type-probe.cjs'))

    def run(case):
        graph = LGraph(None, None, None)
        outer = LGraph(None, None, None)
        parent = LNode(outer)
        nodes, ports = {}, {}
        for name in ('pe0', 'pe1', 'pw0', 'pw1'):
            port = LPort()
            set_port_owner(port, parent)
            set_side(port, 'EAST' if name[1] == 'e' else 'WEST')
            ports[name] = port
        for item in case['nodes']:
            node = LNode(graph)
            node.type = item['type']
            nodes[item['id']] = node
            for name, side in item['ports']:
                port = LPort()
                set_port_owner(port, node)
                set_side(port, side)
                ports[name] = port
        for item in case['nodes']:
            if 'origin' in item:
                nodes[item['id']].properties['ORIGIN'] = ports[item['origin']]
        order = []
        for names in case['layers']:
            layer = Layer(graph)
            graph.layers.append(layer)
            row = []
            for name in names:
                node = nodes[name]
                set_layer(node, layer)
                row.append(node)
            order.append(row)
        edges = list(case['edges'])
        if 'repeatEdge' in case:
            repeated = case['repeatEdge']
            edges += [(repeated['source'], repeated['target'])] * repeated['count']
        for a, b in edges:
            edge = LEdge()
            set_source(edge, ports[a])
            set_target(edge, ports[b])
        for port, dummy in case['portDummies']:
            ports[port].properties['PORT_DUMMY'] = nodes[dummy]
        graph.properties['CROSSING_MINIMIZATION_HIERARCHICAL_SWEEPINESS'] = case['boundary']
        deterministic_calls = []
        def deterministic():
            deterministic_calls.append(1)
            return False
        data = SimpleNamespace(l_graph=graph, parent=parent, has_parent=True,
            current_node_order=order, cross_minimizer=SimpleNamespace(is_deterministic=deterministic))
        decider = LayerSweepTypeDecider(data)
        for li, row in enumerate(order):
            decider.init_at_layer_level(li, order)
            for ni in range(len(row)):
                decider.init_at_node_level(li, ni, order)
        decision = decider.use_bottom_up()
        def view(name):
            node = nodes[name]
            info = decider.node_info[node.layer.id][node.id]
            return dict(id=name, connected=info.connected_edges,
                hierarchical=info.hierarchical_influence, random=info.random_influence)
        return dict(decision=decision, deterministicCalls=len(deterministic_calls),
            info=[[view(name) for name in names] for names in case['layers']],
            layoutExecuted=False, suppliedStrategyFact='non-deterministic')

    cases = [case for case in spec['cases'] if selected_case is None or case['id'] == selected_case]
    assert cases and (selected_case is None or len(cases) == 1)
    actual = [dict(id=case['id'], value=run(case)) for case in cases]
    expected_rows = [row for row in expected['results']
        if selected_case is None or row['id'] == selected_case]
    # These three fields are source JS Number accumulators, not integer IDs.
    # JSON.stringify may emit an integer-looking shortest decimal above 2**53;
    # decode that decimal to the source binary64 value before exact comparison.
    decoded = json.loads(json.dumps(expected_rows))
    for row in decoded:
        for layer in row['value']['info']:
            for info in layer:
                for key in ('connected', 'hierarchical', 'random'):
                    assert type(info[key]) in (int, float)
                    info[key] = float(info[key])
    comparison = diff(decoded, actual)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=decoded,
        originalNumberWireObservation=expected_rows, selectedCase=selected_case,
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='New real deferred NS influence, external-port paths, zero-path Infinity decision and 61 live self transfers; supplied non-determinism is an intermediate strategy fact, not full GraphInfo/sweep')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
