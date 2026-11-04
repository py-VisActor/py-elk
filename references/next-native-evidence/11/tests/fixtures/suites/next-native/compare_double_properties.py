"""Compare new generic DOUBLE import cases; never execute provider layout.

Usage: python compare_double_properties.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import traceback


def main():
    source,request,oracle,report=map(Path,sys.argv[1:5]);selected=sys.argv[5] if len(sys.argv)>5 else None
    source=source.resolve();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def tree():
        return {p.relative_to(source).as_posix():sha(p) for p in source.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    before=tree();sys.path.insert(0,str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    expected=json.loads(oracle.read_bytes());assert expected['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert expected['requestSha256']==sha(request) and expected['probeSha256']==sha(request.with_name('double-properties-probe.cjs'))
    rows=[]
    for spec,row in zip(json.loads(request.read_bytes())['cases'],expected['results'],strict=True):
        assert spec['id']==row['id']
        if selected and selected!=spec['id']:continue
        result={'id':spec['id']}
        try:
            graph={'id':'root','layoutOptions':{spec['option']:json.loads(spec['literal'])}}
            state=JsonLayoutSession(graph);value=state.option(state.graph,spec['option'])
            actual={'present':state.has_option(state.graph,spec['option']),'value':value,
                    'negativeZero':value==0 and math.copysign(1,value)<0,'plusOne':value+1}
            comparison=diff(row['result'],actual,tolerant=False)
            result.update(actual=actual,strictDifference=comparison,passed=comparison['passed'])
        except Exception as error:
            result.update(passed=False,errorType=type(error).__name__,error=str(error),traceback=traceback.format_exc())
        rows.append(result)
    assert rows and (not selected or len(rows)==1)
    after=tree();assert before==after
    data={'passed':all(r['passed'] for r in rows),'rows':rows,'sourceBefore':before,'sourceAfter':after,
          'comparatorSha256':sha(Path(__file__)),'requestSha256':sha(request),'oracleSha256':sha(oracle),
          'modulePath':str(Path(sys.modules[JsonLayoutSession.__module__].__file__).resolve()),'pid':os.getpid(),
          'parentPid':os.getppid(),'layoutExecuted':False,'fullValidation':False,'publicAPIIntegrated':False}
    with report.open('x',encoding='utf8') as file:json.dump(data,file,indent=2,allow_nan=False)
    print(json.dumps({'passed':data['passed'],'caseCount':len(rows),'failedCases':[r['id'] for r in rows if not r['passed']]}))
    return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
