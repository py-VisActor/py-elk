"""Run only new geometric value, triangulation and naive-tree object controls.

Usage: python -I compare_triangulation.py PRIVATE_SRC REQUEST ORACLE REPORT
Original expected observations are collected separately with the fixed worker.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.triangulation import Vec2, TEdge, TTriangle, ValueSet, value_hash, triangulate, create_spanning_tree
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('triangulation-probe.cjs'))
    rows = []
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        row = dict(id=case['id'])
        try:
            points = [Vec2(*p) for p in case['points']]
            index = lambda p: next((i for i, v in enumerate(points) if v is p), -1)
            def number(v):
                if math.isnan(v): return 'NaN'
                if math.isinf(v): return 'Infinity' if v > 0 else '-Infinity'
                if v == 0 and math.copysign(1, v) < 0: return '-0'
                return v
            encoded = lambda p: [number(p.x), number(p.y)]
            edges = lambda es: [[index(e.u), index(e.v)] for e in es]
            op = case['operation']
            if op == 'hashes':
                value = dict(hashes=[value_hash(p) for p in points], coordinates=list(map(encoded, points)))
            elif op == 'buckets':
                values = ValueSet(points)
                snapshot = lambda: [index(p) for p in values]
                steps = [snapshot()]
                removed_first = values.remove(points[0]); steps.append(snapshot())
                removed_last = values.remove(points[2]); steps.append(snapshot())
                readded = values.add(points[0]); steps.append(snapshot())
                duplicate = values.add(Vec2(points[0].x, points[0].y)); steps.append(snapshot())
                value = dict(steps=steps, removedFirst=removed_first, removedLastCollision=removed_last,
                             readded=readded, duplicate=duplicate, size=len(values))
            elif op == 'triangle':
                broad, repeated = TTriangle(*points), TTriangle(points[0], points[0], points[0])
                named = lambda xs: ['broad' if x is broad else 'repeated' for x in xs]
                value = dict(broadEqualsRepeated=broad.source_equals(repeated), repeatedEqualsBroad=repeated.source_equals(broad),
                             hashes=[value_hash(broad), value_hash(repeated)], circumcenters=[encoded(broad.circumcenter), encoded(repeated.circumcenter)],
                             insertBroadThenRepeated=named(ValueSet([broad, repeated])), insertRepeatedThenBroad=named(ValueSet([repeated, broad])))
            elif op == 'triangulate':
                value = dict(edges=edges(triangulate(points)))
            else:
                es = [TEdge(points[a], points[b]) for a, b in case['edges']]
                values = ValueSet(es); calls = []
                def cost(edge):
                    i = next(i for i, e in enumerate(es) if e is edge)
                    calls.append(i)
                    return case['costs'][i]
                result = create_spanning_tree(values, points[case['root']], cost)
                def tree(t): return dict(node=index(t.node), children=list(map(tree, t.children)))
                value = dict(inputEdgeOrder=edges(values), costCalls=calls, tree=tree(result))
            value['fullLayoutValidated'] = False
            row.update(actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences'])
        except Exception as error:
            row.update(errorType=type(error).__name__, error=str(error), traceback=traceback.format_exc(), differences=[{'kind': 'native-exception'}])
        rows.append(row)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullValidation=False,
                  scope='Geometric value/hash bucket, actual Bowyer-Watson and naive MST object helpers only; no complete provider or geometric admission claim')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[r['id'] for r in rows if r['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
