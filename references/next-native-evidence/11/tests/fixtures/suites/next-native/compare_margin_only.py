"""Compare actual margin-only hook against original NodeMarginCalculator.

Usage: python compare_margin_only.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.execution.node_micro import _PropertyReader, _Node
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == sha(request)
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['probeSha256'] == sha(request.with_name('margin-only-probe.cjs'))
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']: continue
        state = JsonLayoutSession(s['graph'])
        reader = _PropertyReader(state)
        class Graph:
            properties = {}
        def shape(data):
            return dict(id=data['id'], pos=[data['x'], data['y']], size=[data['width'], data['height']],
                        labels=[dict(pos=[l['x'], l['y']], size=[l['width'], l['height']]) for l in data.get('labels', [])])
        def snapshot():
            result = []
            for data in state.graph.get('children', []):
                n = _Node(reader, data, Graph())
                result.append(dict(shape=shape(data), ports=[dict(shape=shape(p.data), compoundConnections=p._inside()) for p in n.ports]))
            return result
        value = dict(before=snapshot())
        state.calculate_node_margins(state.graph)
        value['after'] = snapshot()
        assert diff(value['before'], value['after'])['passed'], 'Margin-only changed geometry/order'
        value['margins'] = []
        for data in state.graph.get('children', []):
            margin = reader.get(data, 'node', 'margins')
            value['margins'].append([margin.top, margin.right, margin.bottom, margin.left])
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    assert rows and (not selected or len(rows) == 1)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if name == 'pyelk' or name.startswith('pyelk.') if getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported}, sourceTreeUnchanged=unchanged,
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
                  scope='Only actual margin calculation, without sort/size/commit; no provider layout/public API acceptance')
    with report.open('x', encoding='utf8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
