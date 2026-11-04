"""Compare only the new finite-geometry binary64 import path.

Usage: python compare_numeric_import.py PRIVATE_SRC REQUEST ORACLE REPORT
Original observations are read by this development tool, never by runtime code.
"""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    source=source.resolve()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    def tree():
        return {p.relative_to(source).as_posix():sha(p) for p in source.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    before=tree();sys.path.insert(0,str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk._errors import ModelValidationError
    sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
    from layout_checks import diff
    expected=json.loads(oracle.read_bytes())
    assert expected['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert expected['requestSha256']==sha(request)
    assert expected['probeSha256']==sha(request.with_name('numeric-import-probe.cjs'))
    rows=[]
    for case, observation in zip(json.loads(request.read_bytes())['cases'],expected['cases'],strict=True):
        assert case['id']==observation['id']
        # The native object API can represent signed zero with float(-0.0).
        # Other integer literals remain Python ints until the importer runs.
        values={k:(-0.0 if v=='-0' else json.loads(v)) for k,v in case['literals'].items()}
        graph=dict(id=2**53+1,business={'exactInteger':2**53+1},**values)
        original=copy.deepcopy(graph);state=JsonLayoutSession(graph)
        actual_shape={k:state.graph[k] for k in values}
        actual={'imported':actual_shape,
                'negativeZero':{k:value==0 and math.copysign(1,value)<0 for k,value in actual_shape.items()},
                'widthPlusOne':state.graph['width']+1,'xPlusOne':state.graph['x']+1}
        comparison=diff(observation['result'],actual,tolerant=False)
        assert all(type(v) is float for v in actual_shape.values())
        point=state._point({'x':2**53+1,'y':-0.0},'/hostControl')
        assert point['x']==2**53 and type(point['x']) is float and math.copysign(1,point['y'])<0
        exported=state.export()
        assert exported['id']==graph['id'] and type(exported['id']) is int
        assert exported['business']==graph['business'] and graph==original
        rows.append({'id':case['id'],'actual':actual,'strictDifference':comparison,
                     'typedIdAndBusinessPreserved':True,'inputPreserved':True,'passed':comparison['passed']})
    for value in (True,math.nan,math.inf,10**400):
        try:JsonLayoutSession({'id':'invalid','width':value})
        except ModelValidationError:pass
        else:raise AssertionError('Finite geometry input policy changed')
    after=tree();assert before==after
    result={'passed':all(r['passed'] for r in rows),'caseCount':len(rows),'rows':rows,
            'sourceBefore':before,'sourceAfter':after,'oracleSha256':sha(oracle),'requestSha256':sha(request),
            'comparatorSha256':sha(Path(__file__)),'modulePath':str(Path(sys.modules[JsonLayoutSession.__module__].__file__).resolve()),
            'pid':os.getpid(),'parentPid':os.getppid(),'fullValidation':False,'layoutExecuted':False,
            'sourceWireOrWholeNumberLayerAccepted':False,'publicAPIIntegrated':False}
    with report.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps({'passed':result['passed'],'caseCount':len(rows),'fullValidation':False}))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
