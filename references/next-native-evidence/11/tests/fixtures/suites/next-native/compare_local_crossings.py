"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual local crossing queries only."""
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
    from pyelk.algorithms.layered import crossing_counter as module
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    spec = json.loads(request.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('local-crossings-probe.cjs'))

    def run(operation):
        graph = LGraph(None, None, None)
        nodes, ports = {}, {}
        for item in spec['nodes']:
            node = LNode(graph)
            nodes[item['id']] = node
            for name, side in item['ports']:
                port = LPort()
                set_port_owner(port, node)
                set_side(port, side)
                port.id = len(ports)
                ports[name] = port
        names = {port: name for name, port in ports.items()}
        node_names = {node: name for name, node in nodes.items()}
        order = []
        for li, ids in enumerate(spec['layers']):
            layer = Layer(graph, id=li)
            graph.layers.append(layer)
            row = []
            for ni, name in enumerate(ids):
                node = nodes[name]
                node.id = ni
                set_layer(node, layer)
                row.append(node)
            order.append(row)
        for a, b in spec['edges']:
            edge = LEdge()
            set_source(edge, ports[a])
            set_target(edge, ports[b])
        positions = dict.fromkeys(ports.values(), 0)
        counter = module.CrossingsCounter(positions)
        ends = counter.ends
        if operation == 'undefined-side-no-view':
            node = LNode(graph)
            snapshot = lambda: dict(cached=node.port_sides_cached, indices=list(node.port_side_indices))
            state_before = snapshot()
            real = module._side_view
            calls = []
            def delegate(*args):
                calls.append(1)
                return real(*args)
            module._side_view = delegate
            try:
                values = counter._side_ports_in_north_south_order(node, 'UNDEFINED')
            finally:
                module._side_view = real
            return dict(calls=len(calls), empty=not values, before=state_before, after=snapshot())
        if operation == 'ports-both-orders':
            counter.init_for_counting_between(order[0], order[1])
            selected = counter.connected_ports_sorted_by_position(ports['a1'], ports['a2'])
        else:
            counter._init_positions_for_in_layer(order[1], 'WEST')
            selected = counter.connected_in_layer_ports_sorted_by_position(nodes['r'], nodes['s'], 'WEST')
        snapshot = lambda: [dict(id=name, value=positions[port]) for name, port in ports.items()]
        positions_before = snapshot()
        events = []
        real_clear = counter.index_tree.clear
        real_ports = counter.switch_ports
        real_nodes = counter.switch_nodes
        def clear():
            events.append('clear')
            return real_clear()
        def switch_ports(a, b):
            events.append('switchPorts:' + names[a] + ':' + names[b])
            return real_ports(a, b)
        def switch_nodes(a, b, side):
            events.append('switchNodes:' + node_names[a] + ':' + node_names[b])
            return real_nodes(a, b, side)
        counter.index_tree.clear = clear
        counter.switch_ports = switch_ports
        counter.switch_nodes = switch_nodes
        if operation == 'ports-both-orders':
            pair = counter.count_crossings_between_ports_in_both_orders(ports['a1'], ports['a2'])
        else:
            pair = counter.count_in_layer_crossings_between_nodes_in_both_orders(nodes['r'], nodes['s'], 'WEST')
        return dict(selected=[names[p] for p in selected], before=positions_before, after=snapshot(),
            pair=list(pair), events=events,
            tree=dict(size=counter.index_tree.size, sums=counter.index_tree.binary_sums,
                multiplicities=counter.index_tree.nums_per_index),
            endsIdentity=counter.ends is ends, endsEmpty=not counter.ends,
            portOrders=[dict(id=name, ports=[names[p] for p in node.ports]) for name, node in nodes.items()])

    actual = [dict(id=operation, value=run(operation)) for operation in spec['cases']]
    # Source Pair holds GWT Integer objects. This DTO exposes their scalar value,
    # matching the native pair interface; keep the original boxed observation.
    expected = json.loads(json.dumps(original['results']))
    for row in expected:
        if row['id'] != 'undefined-side-no-view':
            boxed = row['value']['pair']
            assert all(type(value) is dict and set(value) == {'value_0'}
                and type(value['value_0']) in (int, float) for value in boxed)
            row['value']['pair'] = [value['value_0'] for value in boxed]
    comparison = diff(expected, actual)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=expected,
        originalBoxedObservation=original['results'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='Only new port/node both-order queries and UNDEFINED side no-view leaf; no old counter reruns or crossing sweep')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
