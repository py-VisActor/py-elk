"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; actual type/individual spacings."""
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
    from pyelk.algorithms.layered.graph import LGraph, LNode, Layer, set_layer
    from pyelk.algorithms.layered import spacings as module
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('spacings-probe.cjs'))
    s = json.loads(request.read_bytes())
    graph = LGraph(None, None, None)
    for key, value in s['graphValues'].items():
        graph.properties[module._PROPERTIES[key].native_key] = float(value)
    spacing = module.Spacings(graph)
    vertical, horizontal = spacing.node_type_spacing_options_vertical, spacing.node_type_spacing_options_horizontal
    def view(matrix):
        return [[None if p is None else p.canonical_id for p in row] for row in matrix]
    queries = []
    for axis, matrix in [('vertical', vertical), ('horizontal', horizontal)]:
        for a in range(len(module.NODE_TYPES)):
            for b in range(len(module.NODE_TYPES)):
                if matrix[a][b] is not None:
                    getter = spacing.get_vertical_spacing if axis == 'vertical' else spacing.get_horizontal_spacing
                    queries.append(dict(axis=axis, a=a, b=b, value=getter(module.NODE_TYPES[a], module.NODE_TYPES[b])))
    first, second = LNode(graph), LNode(graph)
    second.type = 'LONG_EDGE'
    canonical = module._PROPERTIES['SPACING_EDGE_NODE'].canonical_id
    first.properties['SPACING_INDIVIDUAL'] = {canonical:float(s['individualValues'][0])}
    second.properties['SPACING_INDIVIDUAL'] = {canonical:float(s['individualValues'][1])}
    calls, pairs = [], []
    saved = module.get_individual_or_default
    def traced(node, prop):
        calls.append('first' if node is first else 'second')
        return saved(node, prop)
    module.get_individual_or_default = traced
    try:
        pairs.append(spacing.get_vertical_spacing_nodes(first, second))
        del second.properties['SPACING_INDIVIDUAL']
        pairs.append(spacing.get_vertical_spacing_nodes(first, second))
        del first.properties['SPACING_INDIVIDUAL']
        set_layer(second, Layer(graph))
        second.graph = None
        pairs.append(spacing.get_vertical_spacing_nodes(first, second))
    finally:
        module.get_individual_or_default = saved
    actual = dict(vertical=view(vertical), horizontal=view(horizontal), queries=queries,
        pairs=pairs, calls=calls, individualAbsentAfterRemove=all('SPACING_INDIVIDUAL' not in n.properties for n in (first,second)),
        layerGraphFallback=module._graph(second) is graph, sourceObjectApi=True, layoutExecuted=False)
    comparison = diff(original['observation'], actual, tolerant=False)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(p in before and sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['observation'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
        inputsSha256={str(p):sha(p) for p in (Path(__file__), request, oracle)}, checkerSha256=sha(Path(__file__)),
        scope='Actual two nullable property matrices, all assigned type getters and three concrete node-pair reads; no layout',
        layoutExecuted=False, fullValidation=False)
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
