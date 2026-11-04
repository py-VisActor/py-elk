"""Compare new numeric-root, same-session Box and minimum-only boundaries.

Usage: python compare_host_boundaries.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
Each case invokes only its own newly introduced host boundary.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import traceback


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve(); sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms.spore import SporeImporter
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request) and original['probeSha256'] == sha(request.with_name('host-boundaries-probe.cjs'))
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']: continue
        saved = copy.deepcopy(s['graph']); state = JsonLayoutSession(s['graph'])
        def shape(node):
            return dict(id=state.identifier_text(node), pos=[node['x'], node['y']], size=[node['width'], node['height']],
                        labels=[dict(pos=[label['x'], label['y']], size=[label['width'], label['height']]) for label in node.get('labels', [])])
        def snapshot():
            return dict(root=shape(state.graph), children=[dict(shape=shape(node), ports=[shape(port) for port in node.get('ports', [])])
                        for node in state.graph.get('children', [])])
        row = dict(id=s['id'])
        try:
            if s['operation'] == 'numeric-root':
                graph = SporeImporter().import_graph(state, state.graph)
                value = dict(selectedIndex=graph.vertices.index(graph.preferred_root),
                             identifierViews=[state.identifier_text(node) for node in state.graph['children']],
                             rawIds=[node['id'] for node in state.graph['children']], fullLayoutValidated=False)
                assert type(value['rawIds'][1]) is int
            elif s['operation'] == 'invoke-box':
                state.computed_options.setdefault(id(state.graph), {})['_v_host_marker'] = 17
                first = snapshot(); algorithm = state.graph['layoutOptions']['org.eclipse.elk.algorithm']
                unknown = state.invoke_layout(state.graph, 'unknown.native.provider')
                known = state.invoke_layout(state.graph, 'box')
                value = dict(before=first, after=snapshot(), unknownResolved=unknown, knownResolved=known,
                             marker=state.computed_options[id(state.graph)]['_v_host_marker'], algorithmBefore=algorithm,
                             algorithmAfter=state.graph['layoutOptions']['org.eclipse.elk.algorithm'], underlyingProviderExecuted='box', fullLayoutValidated=False)
            else:
                first = snapshot(); size = state.label_node_minimum(state.graph['children'][0]); second = snapshot()
                assert diff(first, second)['passed'], 'Minimum query changed geometry/order'
                value = dict(before=first, after=second, minimum=[size.x, size.y], applyStuff=False, ignoreInsidePortLabels=True, fullLayoutValidated=False)
            assert diff(saved, s['graph'])['passed'], 'Host boundary changed caller input'
            row.update(actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences'])
        except Exception as error:
            row.update(errorType=type(error).__name__, error=str(error), traceback=traceback.format_exc(), differences=[{'kind': 'host-exception'}])
        rows.append(row)
    assert rows and (not selected or len(rows) == 1)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullValidation=False,
                  scope='Only new source identifier selection, real same-session Box invocation and process(false,true) minimum query; no complete macro provider')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
