"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: one actual crossing phase only."""
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
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.phases import JavaRandom
    from pyelk.algorithms.layered.layer_sweep import LayerSweepCrossingMinimizer
    from pyelk.algorithms.layered.all_crossings import AllCrossingsCounter
    from pyelk.execution.diagnostics import BasicProgressMonitor
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    s = json.loads(request.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('sweep-phase-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes, ports = {}, {}
    for item in s['nodes']:
        node = LNode(graph)
        nodes[item['id']] = node
        for name, side in item['ports']:
            port = LPort()
            set_port_owner(port, node)
            set_side(port, side)
            ports[name] = port
    node_names = {node: name for name, node in nodes.items()}
    port_names = {port: name for name, port in ports.items()}
    layers = []
    for names in s['layers']:
        layer = Layer(graph)
        graph.layers.append(layer)
        layers.append(layer)
        for name in names:
            set_layer(nodes[name], layer)
    for a, b in s['edges']:
        edge = LEdge()
        set_source(edge, ports[a])
        set_target(edge, ports[b])
    graph.random = rng = JavaRandom(s['seed'])
    graph.properties['THOROUGHNESS'] = s['thoroughness']
    controller = LayerSweepCrossingMinimizer('BARYCENTER')
    monitor = BasicProgressMonitor()
    bits, counts, sweeps = [], [], []
    real_next, real_count, real_sweep = rng.next, AllCrossingsCounter.count_all_crossings, controller.sweep_reducing_crossings
    def record_next(count):
        bits.append(count)
        return real_next(count)
    def record_count(counter, order):
        returned = real_count(counter, order)
        counts.append(returned)
        return returned
    def record_sweep(data, forward, first):
        returned = real_sweep(data, forward, first)
        sweeps.append(dict(forward=forward, first=first, returned=returned))
        return returned
    rng.next, AllCrossingsCounter.count_all_crossings, controller.sweep_reducing_crossings = record_next, record_count, record_sweep
    error = None
    try:
        controller.process(graph, monitor)
    except Exception as caught:
        error = dict(type=type(caught).__name__, message=str(caught), traceback=traceback.format_exc())
    finally:
        rng.next, AllCrossingsCounter.count_all_crossings = real_next, real_count
    if error is None:
        data = controller.graph_info_holders[0]
        def view(snapshot):
            if snapshot is None: return None
            return dict(nodes=[[node_names[n] for n in row] for row in snapshot.node_order],
                ports=[[[port_names[p] for p in ps] for ps in row] for row in snapshot.port_orders])
        actual = dict(order=[[node_names[n] for n in layer.nodes] for layer in layers],
            current=[[node_names[n] for n in row] for row in data.current_node_order],
            ports=[dict(id=name, ports=[port_names[p] for p in n.ports], constraint=n.properties.get('PORT_CONSTRAINTS', 'UNDEFINED')) for name, n in nodes.items()],
            best=view(getattr(data, 'best_node_and_port_order', None)),
            currentlyBest=view(getattr(data, 'currently_best_node_and_port_order', None)),
            bits=bits, counts=counts, sweeps=sweeps, rngState=[rng.seedhi, rng.seedlo],
            monitor=dict(name=monitor.task_name, closed=monitor._closed),
            flags=dict(first=graph.properties.get('FIRST_TRY_WITH_INITIAL_ORDER', False),
                second=graph.properties.get('SECOND_TRY_WITH_INITIAL_ORDER', False)),
            layoutExecuted=False, crossingPhaseExecuted=True)
        comparison = diff(original['observation'], actual)
    else:
        actual = dict(error=error, bits=bits, counts=counts, sweeps=sweeps)
        comparison = dict(passed=False, differences=[dict(kind='candidate-error', error=error)])
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, crossingPhaseExecuted=True, fullValidation=False,
        scope='One new complete BARYCENTER crossing phase on supplied K3,3 intermediate graph, real three restarts/counts/RNG/snapshots/final transfer. No full JSON layout, weighted cost or unsupported strategy claim')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
