"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: real weighted model-order costs."""
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
    from pyelk.algorithms.layered.model_order_ports import ModelOrderPortComparator
    from pyelk.algorithms.layered.model_order_targets import long_edge_target_node_preprocessing
    from pyelk.algorithms.layered import model_order_cost as costs
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('model-order-cost-probe.cjs'))
    graph = LGraph(None, None, None)
    nodes, ports = {}, {}
    for item in s['nodes']:
        node = nodes[item['id']] = LNode(graph)
        node.properties['MODEL_ORDER'] = item['modelOrder']
        for name, side, order in item['ports']:
            port = ports[name] = LPort()
            set_port_owner(port, node)
            set_side(port, side)
            port.properties['MODEL_ORDER'] = order
    for index, names in enumerate(s['layers']):
        layer = Layer(graph, id=index)
        graph.layers.append(layer)
        for name in names:
            set_layer(nodes[name], layer)
    for a, b, order in s['edges']:
        edge = LEdge()
        set_source(edge, ports[a])
        set_target(edge, ports[b])
        edge.properties['MODEL_ORDER'] = order
    graph.random = JavaRandom(s['seed'])
    graph.properties.update(MAX_MODEL_ORDER_NODES=len(nodes),
        CONSIDER_MODEL_ORDER_STRATEGY=s['strategy'], CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER=True,
        CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE=s['nodeInfluence'],
        CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE=s['portInfluence'])
    controller = LayerSweepCrossingMinimizer('BARYCENTER')
    data = GraphInfoHolder(graph, 'BARYCENTER', [])
    controller.graph_info_holders = [data]
    node_cost = costs.count_model_order_node_changes(graph, data.current_node_order, s['strategy'])
    port_cost = costs.count_model_order_port_changes(graph, data.current_node_order)
    events = []
    node_real, port_real = costs.count_model_order_node_changes, costs.count_model_order_port_changes
    count_real = data.crossings_counter.count_all_crossings
    def node_count(*args):
        events.append('node-cost')
        return node_real(*args)
    def port_count(*args):
        events.append('port-cost')
        return port_real(*args)
    def count(order):
        events.append('all')
        return count_real(order)
    costs.count_model_order_node_changes, costs.count_model_order_port_changes = node_count, port_count
    data.crossings_counter.count_all_crossings = count
    try:
        score = controller.count_current_number_of_crossings(data, weighted=True)
    finally:
        costs.count_model_order_node_changes, costs.count_model_order_port_changes = node_real, port_real
        data.crossings_counter.count_all_crossings = count_real
    pc = ModelOrderPortComparator(graph, data.current_node_order[0], s['strategy'])
    self_port = ports[s['selfPort']]
    self_results = [pc.compare(self_port, self_port), pc.compare(self_port, self_port)]
    targets = []
    for name, node in nodes.items():
        values = long_edge_target_node_preprocessing(node)
        targets.append(dict(id=name, memoIdentity=values is long_edge_target_node_preprocessing(node),
            values=[values[n].value if n in values else None for n in nodes.values()]))
    node_ids = {node: name for name, node in nodes.items()}
    actual = dict(nodeCost=node_cost, portCost=port_cost, score=score, events=events,
        selfResults=self_results, selfCache=self_port in pc.bigger_than[self_port], targets=targets,
        portTargets=[[name, node_ids.get(port.properties.get('LONG_EDGE_TARGET_NODE'))] for name, port in ports.items()],
        nodeOrder=[[node_ids[n] for n in row] for row in data.current_node_order],
        layoutExecuted=False, suppliedInternalModelOrder=True)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='New real weighted costs, actual AllCounter, target memo and self-comparison; supplied working-graph MODEL/MAX values, not JSON import or complete layout')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
