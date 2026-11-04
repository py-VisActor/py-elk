"""Compare real rank production and distribution against saved originals.

Usage: python -I compare_port_distribution.py PRIVATE_SRC REQUEST ORACLE REPORT
The supplied graph is intermediate state; no rank values are supplied.
"""
import hashlib
import json
from pathlib import Path
import sys
import traceback


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, LEdge, Layer, set_layer, set_port_owner, set_source, set_target
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.port_distribution import NodeRelativePortDistributor, LayerTotalPortDistributor
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes()); spec = json.loads(request.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('port-distribution-probe.cjs'))
    rows = []
    for case, expected in zip(spec['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        row = dict(id=case['id'])
        try:
            graph = LGraph(None, None, None)
            layers = [Layer(graph, id=i) for i in range(len(spec['layers']))]; graph.layers.extend(layers)
            nodes, ports, names = {}, {}, {}
            for item in spec['nodes']:
                node = LNode(graph); nodes[item['id']] = node
                for name, side in item['ports']:
                    port = LPort(); set_port_owner(port, node); set_side(port, side)
                    ports[name] = port; names[port] = name
            order = [[nodes[name] for name in layer] for layer in spec['layers']]
            for i, layer in enumerate(order):
                for node in layer: set_layer(node, layers[i])
            for a, b in spec['edges']:
                edge = LEdge(); set_source(edge, ports[a]); set_target(edge, ports[b])
            dummy = spec['dummy']
            ports[dummy['port']].properties['PORT_DUMMY'] = nodes[dummy['node']]
            for name in dummy['originPorts']: ports[name].properties['ORIGIN'] = ports[dummy['port']]
            cls = NodeRelativePortDistributor if case['kind'] == 'NodeRelative' else LayerTotalPortDistributor
            distributor = cls(len(order))
            for li, layer in enumerate(order):
                distributor.init_at_layer_level(li, order)
                for ni, node in enumerate(layer):
                    distributor.init_at_node_level(li, ni, order)
                    for pi, port in enumerate(node.ports): distributor.init_at_port_level(li, ni, pi, order)
            distributor.init_after_traversal()
            for name, value in spec['oldBarycenters'].items(): distributor.port_barycenters[ports[name]] = value
            def snapshot():
                return dict(ranks=[dict(id=name, value=distributor.port_ranks[port]) for name, port in ports.items()],
                            barycenters=[dict(id=name, value=distributor.port_barycenters[port]) for name, port in ports.items()],
                            portOrder=[dict(id=name, ports=[names[port] for port in node.ports]) for name, node in nodes.items()],
                            positions=distributor.node_positions, min=distributor.min_barycenter, max=distributor.max_barycenter)
            # Serialize snapshots to own all lists; later sweeps mutate positions.
            snap = lambda: json.loads(json.dumps(snapshot(), allow_nan=False))
            stages = [snap()]; returned = None
            if case['operation'] == 'rank':
                for layer, direction in ((order[1], 'INPUT'), (order[0], 'OUTPUT'), (order[1], 'INPUT')):
                    distributor.calculate_port_ranks(layer, direction); stages.append(snap())
            else:
                returned = distributor.distribute_ports_while_sweeping(order, 1, True); stages.append(snap())
            value = dict(stages=stages, returned=returned, rankProducerExecuted=True, fullLayoutValidated=False)
            row.update(actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences'])
        except Exception as error:
            row.update(errorType=type(error).__name__, error=str(error), traceback=traceback.format_exc(), differences=[{'kind':'native-exception'}])
        rows.append(row)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullLayoutValidated=False,
                  rankProducerExecuted=True, scope='Real rank producer plus NS/in-layer source port distribution on supplied intermediate graph; no crossing counter or scheduler')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[r['id'] for r in rows if r['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
