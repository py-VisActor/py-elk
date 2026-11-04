"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: nested real greedy live swap."""
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
    from pyelk.algorithms.layered.greedy_port_distribution import GreedyPortDistributor
    from pyelk.algorithms.layered.two_node_crossings import BetweenLayerEdgeTwoNodeCrossingsCounter
    from pyelk.algorithms.layered.all_crossings import AllCrossingsCounter, initialize_crossing_receivers
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('greedy-ports-probe.cjs'))
    graph = LGraph(None, None, None)
    parent = LNode(graph); layer = Layer(graph); graph.layers.append(layer); set_layer(parent, layer)
    ports = {}
    for name in s['parentPorts']:
        port = ports[name] = LPort(); set_port_owner(port, parent); set_side(port, 'WEST')
    inner = LGraph(None, None, None); parent.nested_graph = inner; inner.parent_node = parent
    nodes, endpoints = {}, {}
    for index, names in enumerate(s['innerLayers']):
        layer = Layer(inner, id=index); inner.layers.append(layer)
        for name in names:
            node = nodes[name] = LNode(inner, type='EXTERNAL_PORT' if index == 0 else 'NORMAL'); set_layer(node, layer)
            port = endpoints[name] = LPort(); set_port_owner(port, node); set_side(port, 'EAST' if index == 0 else 'WEST')
    for a, b in s['innerEdges']:
        edge = LEdge(); set_source(edge, endpoints[a]); set_target(edge, endpoints[b])
    for p, n in s['dummyForPort']: ports[p].properties['PORT_DUMMY'] = nodes[n]
    order = [[parent]]; all_counter = AllCrossingsCounter(order); distributor = GreedyPortDistributor()
    initialize_crossing_receivers([all_counter, distributor], order)
    names = {port: name for name, port in ports.items()}; before_ports = [names[p] for p in parent.ports]
    events = []
    local_real = distributor.crossings_counter.count_crossings_between_ports_in_both_orders
    switch_real = distributor.crossings_counter.switch_ports
    hierarchy_real = BetweenLayerEdgeTwoNodeCrossingsCounter.count_both_side_crossings
    def local(a, b):
        out = local_real(a, b); events.append(['local', names[a], names[b], *out]); return out
    def switch(a, b):
        events.append(['switch', names[a], names[b]]); return switch_real(a, b)
    def hierarchy(counter, *args):
        out = hierarchy_real(counter, *args)
        events.append(['hierarchy', counter.upper_lower_crossings, counter.lower_upper_crossings]); return out
    distributor.crossings_counter.count_crossings_between_ports_in_both_orders = local
    distributor.crossings_counter.switch_ports = switch
    BetweenLayerEdgeTwoNodeCrossingsCounter.count_both_side_crossings = hierarchy
    try:
        improved = distributor.distribute_ports_while_sweeping(order, 0, s['forward'])
    finally:
        BetweenLayerEdgeTwoNodeCrossingsCounter.count_both_side_crossings = hierarchy_real
    actual = dict(before=before_ports, after=[names[p] for p in parent.ports], improved=improved,
        events=events, nPorts=distributor.n_ports,
        sharedSlots=distributor.crossings_counter.port_positions is distributor.port_pos,
        positions=[distributor.port_pos[ports[name]] for name in s['parentPorts']],
        cacheFlag=parent.port_sides_cached, hierarchicalPresent=hasattr(distributor, 'hierarchical_crossings_counter'),
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
        scope='Actual init traversal/local counter plus nested real TwoNode decides and performs live reversed WEST swap; delegates all observed calls, no supplied crossing score')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
