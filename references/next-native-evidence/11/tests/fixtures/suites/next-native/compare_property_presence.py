"""Compare selected-global presence to real original import/visitor data.

Usage: python compare_property_presence.py PRIVATE_SRC REQUEST ORACLE REPORT
No provider or layout is executed.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == sha(request)
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        state = JsonLayoutSession(s['graph'], s.get('globalOptions'))
        root = state.graph; child = root['children'][0]; port = child['ports'][0]; label = child['labels'][0]; edge = state.edges[0]
        has = state.has_option
        before_has = has(edge, 'stress.desiredEdgeLength')
        value = state.option(edge, 'stress.desiredEdgeLength', 100)
        after_has = has(edge, 'stress.desiredEdgeLength')
        actual = dict(rootDesiredHas=has(root, 'stress.desiredEdgeLength'), rootDesired=state.option(root, 'stress.desiredEdgeLength', 100),
                      edgeDesiredHasBefore=before_has, edgeDesired=value, edgeDesiredHasAfter=after_has,
                      rootFixedHas=has(root, 'stress.fixed'), rootFixed=state.option(root, 'stress.fixed', False),
                      childFixedHas=has(child, 'stress.fixed'), childFixed=state.option(child, 'stress.fixed', False),
                      edgeFixedHas=has(edge, 'stress.fixed'), portFixedHas=has(port, 'stress.fixed'), labelFixedHas=has(label, 'stress.fixed'),
                      rootRepulsiveHas=has(root, 'force.repulsivePower'), edgeRepulsiveHas=has(edge, 'force.repulsivePower'),
                      edgeRepulsive=state.option(edge, 'force.repulsivePower', 0))
        # This one protocol field is an actual declared INT; the original GWT
        # observation retains its Integer box. Project only that scalar slot,
        # preserving complete original bytes and all other types/fields.
        projected = dict(expected['value'])
        boxed = projected['edgeRepulsive']
        assert type(boxed) is dict and set(boxed) == {'value_0'} and type(boxed['value_0']) is int
        projected['edgeRepulsive'] = boxed['value_0']
        rows.append(dict(id=s['id'], actual=actual, expected=projected, originalBoxedObservation=expected['value'],
                         differences=diff(projected, actual)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if name == 'pyelk' or name.startswith('pyelk.') if getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not r['differences'] for r in rows), rows=rows,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported}, sourceTreeUnchanged=unchanged,
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
                  scope='Actual imported property presence and selected-global target witness, no layout/provider execution', layoutExecuted=False)
    with report.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[r['id'] for r in rows if r['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
