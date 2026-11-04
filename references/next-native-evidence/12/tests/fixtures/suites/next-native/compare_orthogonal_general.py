"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: actual general Orthogonal phase/leaves."""
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered import orthogonal_general as routing
    from pyelk.algorithms.layered.graph import (LGraph, LNode, LPort, LEdge, Layer, Vec2,
        set_port_owner, set_layer, set_source, set_target)
    from pyelk.algorithms.layered.ports import set_side
    from pyelk.algorithms.layered.phases import JavaRandom
    from pyelk.execution.diagnostics import BasicProgressMonitor
    from pyelk.execution.node_micro import VectorChain
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    s = json.loads(request.read_bytes())
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    probe = request.with_name(request.name.replace('-request.json', '-probe.cjs'))
    assert original['probeSha256'] == sha(probe)
    if 'weights' in s:
        # Explicit internal numeric leaves: not admitted public NaN input or a
        # finite geometry success. Keep nonfinite values in typed numeric views.
        a, b = routing._Segment(), routing._Segment()
        for weight in s['weights']:
            routing._dependency('REGULAR', a, b, weight)
        sources, sinks = routing._initialize([a, b], False)
        decode = lambda value: math.nan if value == 'NaN' else value
        minimum = routing._minimum_difference(map(decode, s['minimumDifference']))
        generator = routing._Generator(6)
        edge, segment = LEdge(), routing._Segment()
        segment.start, segment.end = s['junction']['segmentStart'], s['junction']['segmentEnd']
        point = Vec2(decode(s['junction']['x']), s['junction']['y'])
        for _ in range(s['junction']['repeats']):
            generator._junction(edge, segment, point)
        def number(value):
            if math.isnan(value):
                return dict(kind='NaN')
            if math.isinf(value):
                return dict(kind='Infinity' if value > 0 else '-Infinity')
            return dict(kind='finite', value=value, negativeZero=value == 0 and math.copysign(1, value) < 0)
        chain = edge.properties['JUNCTION_POINTS']
        actual = dict(weights=dict(out=a.out_weight, **{'in': b.in_weight}, marks=[a.mark, b.mark],
            sources=['a' if n is a else 'b' for n in sources], sinks=['a' if n is a else 'b' for n in sinks]),
            minimumDifference=number(minimum), junctionCount=len(chain),
            junctions=[dict(x=number(p.x), y=number(p.y)) for p in chain],
            layoutExecuted=False, validFiniteGeometry=False, internalNumericLeavesOnly=True)
    else:
        graph = LGraph(None, None, JavaRandom(s['seed']))
        graph.properties.update(RANDOM=graph.random,
            SPACING_NODE_NODE_BETWEEN_LAYERS=s['spacing']['nodeNode'],
            SPACING_EDGE_EDGE_BETWEEN_LAYERS=s['spacing']['edgeEdge'],
            SPACING_EDGE_NODE_BETWEEN_LAYERS=s['spacing']['edgeNode'])
        nodes, ports, edges = {}, {}, {}
        for item in s['nodes']:
            node = nodes[item['id']] = LNode(graph, type=item['type'])
            node.pos.y, node.size.x, node.size.y = item['y'], item['width'], 4
            node.properties['ALIGNMENT'] = item['alignment']
            if 'externalSide' in item:
                node.properties['EXT_PORT_SIDE'] = item['externalSide']
        for index, item in enumerate(s['layers']):
            layer = Layer(graph, id=index)
            layer.size.x = item['width']
            graph.layers.append(layer)
            for name in item['nodes']:
                set_layer(nodes[name], layer)
        for name, owner, side, y, anchor in s['ports']:
            port = ports[name] = LPort()
            set_port_owner(port, nodes[owner])
            set_side(port, side)
            port.pos.y, port.anchor.y = y, anchor
        for name, a, b in s['edges']:
            edge = edges[name] = LEdge()
            set_source(edge, ports[a])
            set_target(edge, ports[b])
        prior = s['preexistingJunction']
        existing = VectorChain([Vec2(prior['x'], prior['y'])])
        edges[prior['edge']].properties['JUNCTION_POINTS'] = existing
        node_ids = {n: name for name, n in nodes.items()}
        calls, draws = [], []
        route, split, next_int = routing._Generator.route, routing._Generator._split_segments, JavaRandom.next_int
        def track_route(self, graph, left, right, start):
            result = route(self, graph, left, right, start)
            calls.append(dict(kind='gap', left=None if left is None else [node_ids[n] for n in left],
                right=None if right is None else [node_ids[n] for n in right], start=start, slots=result))
            return result
        def track_split(self, dependencies, segments):
            count = len(segments)
            result = split(self, dependencies, segments)
            calls.append(dict(kind='split', dependencies=len(dependencies), before=count,
                after=len(segments), threshold=self.critical_threshold))
            return result
        def track_next(self, bound):
            draws.append(bound)
            return next_int(self, bound)
        routing._Generator.route, routing._Generator._split_segments, JavaRandom.next_int = track_route, track_split, track_next
        monitor = BasicProgressMonitor()
        try:
            routing.orthogonal_edge_router(graph, monitor=monitor)
        finally:
            routing._Generator.route, routing._Generator._split_segments, JavaRandom.next_int = route, split, next_int
        edge_values = []
        for name, _, _ in s['edges']:
            edge = edges[name]
            has = 'JUNCTION_POINTS' in edge.properties
            edge_values.append(dict(id=name, bends=[[p.x, p.y] for p in edge.bend_points],
                hasJunction=has, junctions=[[p.x, p.y] for p in edge.properties['JUNCTION_POINTS']] if has else None))
        actual = dict(width=graph.size.x,
            nodes=[dict(id=item['id'], x=nodes[item['id']].pos.x, y=nodes[item['id']].pos.y) for item in s['nodes']],
            edges=edge_values, existingChainPreserved=edges[prior['edge']].properties['JUNCTION_POINTS'] is existing,
            calls=calls, draws=draws, monitor=dict(name=monitor.task_name, closed=monitor._closed),
            layoutExecuted=False, workingGraphPhaseExecuted=True)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual,
        expected=original['observation'], comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='One actual Orthogonal working-graph phase or separately flagged internal numeric leaves; real delegated gap/split/RNG, typed chain identity, no old group replay or public-layout acceptance')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
