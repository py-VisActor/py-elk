"""PRIVATE_SRC REQUEST ORACLE REPORT: actual explicit global/local targets.

This is an independent new configurator/import witness, not a layout. Source
runtime-$H input effects remain separate from native owned-input preservation.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys


def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={p.resolve():sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0,str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.execution.node_micro import _PropertyReader
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    original=json.loads(oracle.read_bytes());spec=json.loads(request.read_bytes());saved=copy.deepcopy(spec)
    assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('generic-targets-probe.cjs'))
    state=JsonLayoutSession(spec['graph'],spec['global']);root=state.graph;a,b=root['children'];port=a['ports'][0];edge=root['edges'][0]
    holders=[('root',root),('a',a),('b',b),('port',port),('edge',edge),('rootLabel',root['labels'][0]),('aLabel',a['labels'][0]),('portLabel',port['labels'][0]),('edgeLabel',edge['labels'][0])]
    keys=['org.eclipse.elk.font.name','org.eclipse.elk.priority','org.eclipse.elk.nodeSize.constraints','org.eclipse.elk.layered.crossingMinimization.semiInteractive']
    rows=[]
    for name,holder in holders:
        properties=[]
        for key in keys:
            present=state.has_option(holder,key)
            properties.append(dict(id=key,present=present,value=state.option(holder,key) if present else None))
        rows.append(dict(id=name,properties=properties))
    reader=_PropertyReader(state);rv=reader.get(root,'node','nodeSize.constraints');av=reader.get(a,'node','nodeSize.constraints');bv=reader.get(b,'node','nodeSize.constraints')
    actual=dict(rows=rows,globalEnumSetShared=rv is bv,localEnumSetIndependent=av is not rv,layoutExecuted=False)
    expected={k:v for k,v in original['value'].items() if k not in ['inputBefore','inputAfter']}
    differences=diff(expected,actual)['differences'];input_preserved=diff(saved,spec)['passed']
    assert input_preserved,'Native import/configuration mutated caller input'
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(sha(p)==before[p] for p in imported)
    source_before=original['value']['inputBefore'];source_after=original['value']['inputAfter']
    result=dict(passed=unchanged and not differences and input_preserved,actual=actual,expected=expected,differences=differences,
                nativeInputPreserved=input_preserved,originalInputBeforeSha256=hashlib.sha256(source_before.encode()).hexdigest(),
                originalInputAfterSha256=hashlib.sha256(source_after.encode()).hexdigest(),originalInputChanged=source_before!=source_after,
                originalInputPolicy='Original before/after raw strings retained in oracle; source runtime identity additions are not rewritten or compared as native-owned-input mutations.',
                sourceTreeUnchanged=unchanged,importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,
                scope='One actual JsonImporter/global configurator witness across9 holder kinds; explicit value/target/presence/enumset sharing only')
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],differences=len(differences),holders=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
