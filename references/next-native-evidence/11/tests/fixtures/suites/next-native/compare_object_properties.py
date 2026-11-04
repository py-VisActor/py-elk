"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT [CASE_ID]; no layout or reference replay."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

source,request_path,oracle_path,output_path=map(Path,sys.argv[1:5])
selected=sys.argv[5]if len(sys.argv)>5 else None
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import pyelk
from layout_checks import diff
from pyelk.options.element import parse_mapping
from pyelk.options.schema import Vector2,VectorChainValue
from pyelk.options.generic import RUNTIME_PROPERTY_SPECS,RAW_CONSTRUCTIBLE_PROPERTY_IDS
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.node_micro import _PropertyReader
from pyelk._errors import UnsupportedOptionError

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert oracle['requestSha256']==sha(request_path)

def point(value):
    return {'x':value.x,'y':value.y,'negativeZeroX':value.x==0 and math.copysign(1,value.x)<0,
            'negativeZeroY':value.y==0 and math.copysign(1,value.y)<0}

parsed=[]
for case in request['parseCases']:
    if selected and selected!=case['id']:continue
    values,_=parse_mapping({case['option']:case['value']},'/layoutOptions')
    value=values[case['option']]
    assert isinstance(value,(Vector2,VectorChainValue))
    points=[value]if isinstance(value,Vector2)else value.points
    parsed.append({'id':case['id'],'cloneable':True,'points':[point(p)for p in points]})
actual={'parsed':parsed}
expected={'parsed':[row for row in oracle['observation']['parsed']if not selected or selected==row['id']]}
if not selected or selected=='clone':
    state=JsonLayoutSession(request['graph'],request['globalOptions']);reader=_PropertyReader(state);e1,e2=state.edges
    one=reader.get(e1,'edge','bendPoints');two=reader.get(e2,'edge','bendPoints');first=one[0];second=two[0]
    present=[state.has_option(e1,'bendPoints'),state.has_option(e2,'bendPoints')]
    first.x=99
    j1=reader.get(e1,'edge','junctionPoints');j2=reader.get(e2,'edge','junctionPoints')
    actual['clone']={'globalChainsDistinct':one is not two,'globalPointsShared':first is second,'mutationVisible':second.x==99,
        'globalPresence':present,'junctionDefaultsDistinct':j1 is not j2,
        'junctionReadCached':reader.get(e1,'edge','junctionPoints') is j1,
        'junctionPresenceAfterRead':[state.has_option(e1,'junctionPoints'),state.has_option(e2,'junctionPoints')],
        'junctionEmpty':not j1 and not j2}
    expected['clone']=oracle['observation']['clone']
    assert state.original==request['graph']
    payload={'native':'opaque algorithm data'}
    state.set_option(state.graph,'resolvedAlgorithm',payload)
    assert reader.get(state.graph,'node','resolvedAlgorithm') is payload
    assert state.option(state.graph,'resolvedAlgorithm') is payload
    state.remove_option(state.graph,'resolvedAlgorithm')
    assert not state.has_option(state.graph,'resolvedAlgorithm')
    assert reader.get(state.graph,'node','resolvedAlgorithm') is None
    assert len(RUNTIME_PROPERTY_SPECS)==243 and len(RAW_CONSTRUCTIBLE_PROPERTY_IDS)==235
    unavailable=[name for name,spec in RUNTIME_PROPERTY_SPECS.items()if spec.kind=='opaque']
    assert len(unavailable)==8
    for name in unavailable:
        try:parse_mapping({name:'{}'},'/layoutOptions')
        except UnsupportedOptionError as error:assert error.code=='UNAVAILABLE_OBJECT_FACTORY'
        else:raise AssertionError('Unavailable original factory was silently accepted')
assert parsed or 'clone'in actual,'Select an existing case'
comparison=diff(expected,actual)
after={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
assert before==after
report={'passed':comparison['passed'],'difference':comparison,'actual':actual,'expected':expected,
        'pid':os.getpid(),'parentPid':os.getppid(),'python':sys.executable,'modulePath':str(Path(pyelk.__file__).resolve()),
        'sourceBeforeSha256':before,'sourceAfterSha256':after,'requestSha256':sha(request_path),'oracleSha256':sha(oracle_path),
        'comparatorSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False,
        'scope':'New position/vector-chain properties, shallow clone and actual unavailable raw factories only; other-owner defaults and public acceptance remain separate'}
with output_path.open('x',encoding='utf-8')as out:json.dump(report,out,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences']),'selected':selected}))
raise SystemExit(0 if comparison['passed']else 1)
