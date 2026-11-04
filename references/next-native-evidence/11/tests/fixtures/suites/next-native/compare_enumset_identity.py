"""Compare saved original EnumSet sharing/presence with the private reader.

Usage: python -I compare_enumset_identity.py PRIVATE_SRC REQUEST ORACLE REPORT
Original type4 is an upstream cast fact, not a field invented for Python.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve(); sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.execution.node_micro import _PropertyReader
    from pyelk.options.schema import generic_spec
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('enumset-identity-probe.cjs'))
    names = ['nodeSize.options', 'nodeLabels.placement']; rows = []
    # This independent imported holder reads actual defaults, without global options.
    baseline = JsonLayoutSession({'id':'default'}); baseline_reader = _PropertyReader(baseline)
    defaults = {name:baseline_reader.get(baseline.graph, 'node', name) for name in names}
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id'] == expected['id']
        state = JsonLayoutSession({'id':'r','children':[{'id':'a'},{'id':'b'}]}, case.get('global'))
        reader = _PropertyReader(state); a, b = state.graph['children']
        properties = []; initial = []
        for name in names:
            canonical = 'org.eclipse.elk.'+name
            # Source before-snapshot occurs before applyVisitors. The native session
            # receives selected globals at construction, so record that boundary
            # separately instead of claiming Python ran a source configurator later.
            initial.append(dict(id=canonical, aHas=reader.has(a,'node',name), bHas=reader.has(b,'node',name)))
            x, y = reader.get(a,'node',name), reader.get(b,'node',name)
            enum_order = generic_spec(canonical).accepted_values
            members = lambda value:[member for member in enum_order if member in value]
            properties.append(dict(id=canonical, sharedBetweenNodes=x is y, sameAsCoreDefault=x is defaults[name],
                                   aHasAfter=reader.has(a,'node',name), bHasAfter=reader.has(b,'node',name),
                                   aMembers=members(x), bMembers=members(y)))
        actual = dict(properties=properties, layoutExecuted=False)
        projected = {k:v for k,v in expected['value'].items() if k!='before'}
        projected['properties'] = [{k:v for k,v in p.items() if k!='type4'} for p in projected['properties']]
        assert all(p['type4'] is False for p in expected['value']['properties'])
        rows.append(dict(id=case['id'], actual=actual, expected=projected,
                         originalBeforeConfigurator=expected['value']['before'], nativeBeforeRead=initial,
                         originalCloneableType4=False, differences=diff(projected,actual)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module,'__file__',None)}
    unchanged = all(sha(p)==before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                  inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)}, layoutExecuted=False,
                  scope='Only shared Core EnumSet defaults/global assignment and property presence; source type4 remains separate upstream fact')
    with report.open('x',encoding='utf-8') as handle: json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
