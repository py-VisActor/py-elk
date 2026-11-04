"""PRIVATE_SRC REQUEST ORACLE REPORT: new original DisCo polygon booleans.

Source tolerance remains a separately recorded source fact; no native constant
is fabricated as if observed. No rasterizer or packing provider executes.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={p.resolve():sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0,str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms.disco import Vec2,Rectangle,DCElement,DCComponent,intersects_path,contains_path
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    original=json.loads(oracle.read_bytes());assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256']==sha(request)
    assert original['probeSha256']==sha(request.with_name('disco-polygon-probe.cjs'))
    rows=[]
    for case,expected in zip(json.loads(request.read_bytes())['cases'],original['results'],strict=True):
        assert case['id']==expected['id']
        assert expected['value']['tolerance']==1e-5
        rectangle=Rectangle(*case['rect']);path=[Vec2(*p) for p in case['path']]
        state=JsonLayoutSession({'id':'identity-owner'});component=DCComponent(state);component.add_elements([DCElement(path)])
        value=dict(intersects=intersects_path(rectangle,path),contains=contains_path(rectangle,path),componentIntersects=component.intersects(rectangle),layoutExecuted=False)
        projected={k:v for k,v in expected['value'].items() if k!='tolerance'}
        rows.append(dict(id=case['id'],actual=value,expected=projected,sourceDeclaredTolerance=expected['value']['tolerance'],differences=diff(projected,value)['differences']))
    imported={Path(m.__file__).resolve() for name,m in tuple(sys.modules.items()) if (name=='pyelk' or name.startswith('pyelk.')) and getattr(m,'__file__',None)}
    unchanged=all(sha(p)==before[p] for p in imported)
    result=dict(passed=unchanged and all(not row['differences'] for row in rows),rows=rows,sourceTreeUnchanged=unchanged,
                importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,
                scope='Only real strict path containment and open segment/polygon predicates; no generic polygon-interior substitute or packing provider')
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
