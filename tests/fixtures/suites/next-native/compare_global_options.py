"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; only changed global import path."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.global_properties import serialize_global_value
from pyelk.algorithms.layered.graph import Vec2,Insets
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert sha(request_path)==oracle['requestSha256']
correction_sha=None
if len(sys.argv)>5:
    correction_path=Path(sys.argv[5]);correction=json.loads(correction_path.read_text('utf-8'))
    assert correction['requestSha256']==oracle['requestSha256']
    assert correction['workerSha256']==oracle['workerSha256']
    assert correction['selectedCase']=='array-enumset-is-invalid'and len(correction['observation'])==1
    oracle['observation']=[correction['observation'][0]if row['name']==correction['selectedCase']else row for row in oracle['observation']]
    correction_sha=sha(correction_path)
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
def normalize(value):
    if isinstance(value,Vec2):return {'x':value.x,'y':value.y,'negativeZeroX':value.x==0 and math.copysign(1,value.x)<0,'negativeZeroY':value.y==0 and math.copysign(1,value.y)<0}
    if isinstance(value,Insets):return {k:getattr(value,k)for k in('top','right','bottom','left')}
    if isinstance(value,(set,frozenset)):return sorted(value)
    return value
actual=[]
for case in request['cases']:
    metadata=NativeMetadataService(case['algorithms'])
    state=JsonLayoutSession(case['graph'],case['options'],metadata=metadata)
    holders=sorted(state._property_holders,key=lambda e:e['id'])
    def snapshot(local_only):
        rows=[]
        for element in holders:
            props=[]
            for name in request['observe']:
                canonical=metadata.lookup_option(name)
                local=state._imported_property_values[id(element)]
                present=canonical is not None and (canonical in local if local_only else state.has_option(element,canonical))
                value=(local[canonical]if local_only else state.get_native_property(element,canonical))if present else None
                props.append({'id':name,'has':present,'value':normalize(value)})
            rows.append({'id':element['id'],'properties':props})
        return rows
    before_values=snapshot(True);after_values=snapshot(False)
    a,b=state.nodes[1:3]
    def identity(name,same):
        return (state.get_native_property(a,name)is state.get_native_property(b,name))is same if state.has_option(a,name)and state.has_option(b,name)else None
    actual.append({'name':case['name'],
      'serialized':[{'key':k,'text':serialize_global_value(v)}for k,v in case['options'].items()if metadata.lookup_option(k)is not None],
      'before':before_values,'after':after_values,
      'configuredVectorCopiesDistinct':identity('nodeSize.minimum',False),
      'configuredEnumSetsShared':identity('nodeSize.constraints',True)})
comparison=diff(oracle['observation'],actual,tolerant=False)
after={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')};assert before==after
imported={}
for module in tuple(sys.modules.values()):
    file=getattr(module,'__file__',None)
    if not file:continue
    p=Path(file).resolve()
    if p.suffix=='.py'and p.is_relative_to(source.resolve()):imported[p.relative_to(source.resolve()).as_posix()]=sha(p)
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceSha256':imported,
 'oracleSha256':sha(oracle_path),'correctedObserverOracleSha256':correction_sha,'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
 'originalReexecuted':False,'layoutExecuted':False,'publicAPIIntegrated':False,'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
