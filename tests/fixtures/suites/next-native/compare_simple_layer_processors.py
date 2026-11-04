"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; two actual working-graph bodies."""
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
    from pyelk.algorithms.layered.graph import LGraph, LNode, Layer, Insets, set_layer
    from pyelk.algorithms.layered import simple_processors as phase
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('simple-layer-processors-probe.cjs'))
    results = []
    for item in json.loads(request.read_bytes())['cases']:
        graph = LGraph(None, None, None)
        graph.offset.y, graph.size.y = item['offsetY'], 999.0
        explicit = None
        if 'surrounding' in item:
            explicit = Insets(*item['surrounding'])
            graph.properties['SPACING_PORTS_SURROUNDING'] = explicit
        names, rows, sizes = {}, [], []
        for input_row in item['layers']:
            layer = Layer(graph)
            graph.layers.append(layer)
            layer.size.x, layer.size.y = 83.0, 97.0
            rows.append(layer.nodes)
            sizes.append(layer.size)
            for value in input_row:
                node = LNode(graph)
                names[node] = value['id']
                node.pos.y, node.size.x, node.size.y = map(float, (value['y'], value['width'], value['height']))
                node.margin = Insets(*map(float, value['margin']))
                node.type = value.get('type', 'NORMAL')
                node.properties['IN_LAYER_CONSTRAINT'] = value['constraint']
                set_layer(node, layer)
        size, offset, layer_list = graph.size, graph.offset, graph.layers
        events, reads = [], []
        class Monitor:
            def begin(self, name, total):
                events.append(dict(kind='begin', name=name, total=total))
            def done(self):
                events.append(dict(kind='done'))
        saved = phase._surrounding_spacing
        def traced(holder):
            value = saved(holder)
            reads.append(value)
            return value
        phase._surrounding_spacing = traced
        try:
            phase.in_layer_constraint_processor(graph, monitor=Monitor())
            phase.layer_size_and_graph_height_calculator(graph, monitor=Monitor())
        finally:
            phase._surrounding_spacing = saved
        has = 'SPACING_PORTS_SURROUNDING' in graph.properties
        margin = graph.properties.get('SPACING_PORTS_SURROUNDING')
        results.append(dict(id=item['id'], events=events,
            rows=[dict(nodes=[names[n] for n in layer.nodes], size=[layer.size.x, layer.size.y],
                       sameList=layer.nodes is rows[i], sameSize=layer.size is sizes[i],
                       sameLayerPointers=all(n.layer is layer for n in layer.nodes))
                  for i, layer in enumerate(graph.layers)],
            height=graph.size.y, offsetY=graph.offset.y,
            sameGraphObjects=graph.size is size and graph.offset is offset and graph.layers is layer_list,
            surrounding=dict(reads=len(reads), has=has,
                value=[margin.top, margin.right, margin.bottom, margin.left] if margin is not None else None,
                sameReadReference=all(v is reads[0] for v in reads),
                explicitReferencePreserved=None if explicit is None else margin is explicit)))
    actual = dict(cases=results, layoutExecuted=False, workingGraphPhaseExecuted=True)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual,
        expected=original['observation'], comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        checkerSha256=sha(Path(__file__)), layoutExecuted=False, workingGraphPhaseExecuted=True,
        scope='Actual native InLayer then LayerSize bodies over supplied graph geometry, four new objects',
        fullValidation=False)
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
