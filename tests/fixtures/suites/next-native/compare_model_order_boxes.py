"""Compare three saved source Integer-box controls without recapturing Node.

Usage: python -I compare_model_order_boxes.py PRIVATE_SRC REQUEST ORACLE REPORT
This is a local comparator identity witness, not full ordering or crossing.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import LGraph, LNode, Layer, set_layer
    from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
    from pyelk.algorithms.layered.model_order_barycenter import ModelOrderBarycenterHeuristic
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('model-order-boxes-probe.cjs'))
    rows = []
    key = 'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID'
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        graph = LGraph(None, None, None, properties={'MAX_MODEL_ORDER_NODES': 10,
            'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY': 'ONLY_WITHIN_GROUP'})
        layer = Layer(graph); graph.layers.append(layer)
        a, b = LNode(graph, id=0), LNode(graph, id=1)
        set_layer(a, layer); set_layer(b, layer)
        for node, order in ((a, 0), (b, 1)):
            node.properties.update(MODEL_ORDER=order)
            node.properties[key] = case['group']
        first = value_of_integer_box(case['group'])
        second = first if case['shared'] else value_of_integer_box(case['group'])
        a.integer_box_identities = {key: first}; b.integer_box_identities = {key: second}
        heuristic = ModelOrderBarycenterHeuristic(None, None, None)
        heuristic.states = {a: SimpleNamespace(barycenter=10), b: SimpleNamespace(barycenter=0)}
        value = dict(sameBox=first is second, firstComparison=heuristic.compare(a, b),
                     repeatedComparison=heuristic.compare(a, b), fullLayoutValidated=False)
        rows.append(dict(id=case['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullLayoutValidated=False,
                  scope='Only source Integer group identity and repeated ModelOrder comparator behavior; supplied intermediate states')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
