"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: new real initializer/dispatch witness."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5]); source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer,
        set_layer, set_port_owner, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.all_crossings import AllCrossingsCounter, initialize_crossing_receivers
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes()); s = json.loads(request.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('all-crossings-probe.cjs'))
    graph = LGraph(None, None, None); nodes = {}; ports = {}; edges = []
    for item in s['nodes']:
        node = LNode(graph); node.type = item.get('type', 'NORMAL'); nodes[item['id']] = node
        for name, side in item['ports']:
            port = LPort(); set_port_owner(port, node); set_side(port, side); ports[name] = port
    order = []
    for li, ids in enumerate(s['layers']):
        layer = Layer(graph, id=li); graph.layers.append(layer); node_order = []
        for name in ids:
            node = nodes[name]; set_layer(node, layer); node_order.append(node)
        order.append(node_order)
    for a, b in s['edges']:
        edge = LEdge(); set_source(edge, ports[a]); set_target(edge, ports[b]); edges.append(edge)
    counters = [AllCrossingsCounter(order), AllCrossingsCounter(order)]
    metadata = lambda c: dict(ns=list(c.has_north_south_ports), hyper=list(c.has_hyper_edges_east_of_index),
        inLayer=list(c.in_layer_edge_counts), ports=c.n_ports)
    metadata_before = [metadata(c) for c in counters]; events = []
    for index, counter in enumerate(counters):
        real = counter.init_at_edge_level
        def delegate(l, n, p, e, edge, all_nodes, index=index, real=real):
            events.append([index, l, n, p, e, edges.index(edge)])
            return real(l, n, p, e, edge, all_nodes)
        counter.init_at_edge_level = delegate
    initialize_crossing_receivers(counters, order)
    metadata_after = [metadata(c) for c in counters]; counter = counters[0]; calls = []
    basic = counter.crossing_counter; hyper = counter.hyperedge_crossings_counter
    in_layer = basic.count_in_layer_crossings_on_side; hyper_count = hyper.count_crossings
    north_south = basic.count_north_south_port_crossings_in_layer
    def record_in_layer(layer, side):
        calls.append('inLayer:' + side); return in_layer(layer, side)
    def record_hyper(left, right):
        calls.append('hyper'); return hyper_count(left, right)
    def record_ns(layer):
        calls.append('northSouth'); return north_south(layer)
    basic.count_in_layer_crossings_on_side = record_in_layer
    hyper.count_crossings = record_hyper
    basic.count_north_south_port_crossings_in_layer = record_ns
    try:
        count = counter.count_all_crossings(order)
    finally:
        basic.count_in_layer_crossings_on_side = in_layer
        hyper.count_crossings = hyper_count
        basic.count_north_south_port_crossings_in_layer = north_south
    actual = dict(before=metadata_before, after=metadata_after, events=events, calls=calls, count=count,
        portIds=[dict(id=name, value=port.id) for name, port in ports.items()],
        sharedBuffers=[c.crossing_counter.port_positions is c.hyperedge_crossings_counter.port_positions for c in counters],
        layoutExecuted=False)
    comparison = diff(original['observation'], actual)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, layoutExecuted=False,
        fullValidation=False, scope='New real two-receiver initializer, typed metadata, duplicate source-port loop incidences and real Hyper/Basic/final-row NS dispatch only; no complete crossing sweep')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
