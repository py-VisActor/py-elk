"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; owned property-only visitor trace."""
import hashlib,json,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.visitors import apply_property_visitors
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert sha(request_path)==oracle['requestSha256']
state=JsonLayoutSession(request['graph']);root=state.graph
alien={'id':request['nativeOnlySetup']['privatePropertyReference']}
state.computed_options.setdefault(id(root),{})['pyelk.privateTraceReference']=alien
classes={'node':'ElkNode','port':'ElkPort','edge':'ElkEdge','label':'ElkLabel'}
def collect():
    trace=[];nodes=[];visited=[]
    def first(current,element):
        trace.append({'visitor':0,'class':classes[state.kinds[id(element)]],'id':state.identifier_text(element)})
        visited.append(element)
        if state.kinds[id(element)]=='node'and state.get_native_property(element,'noLayout'):nodes.append(element['id'])
    def second(current,element):
        trace.append({'visitor':1,'class':classes[state.kinds[id(element)]],'id':state.identifier_text(element)})
    apply_property_visitors(state,[first,second])
    return {'trace':trace,'noLayoutNodes':nodes,'privateReferenceVisited':any(value is alien for value in visited)}
imported=collect();parent=root['labels'][0]
count=sum(state.kinds.get(id(label))=='label'for label in parent.get('labels',()))
label={'id':request['nativeOnlySetup']['manualNestedLabel'],'text':'native nested'}
state._register(label,{},'label',parent,'/internal-owned-label',required_id=False)
state._geometry(label,'/internal-owned-label');parent.setdefault('labels',[]).append(label);state.labels.append(label)
actual={'imported':imported,'withNativeNestedLabel':collect(),'importedNestedLabelCount':count,
 'privatePropertyPresent':state.property_snapshot(root).has('pyelk.privateTraceReference'),
 'privatePropertySame':state.property_snapshot(root).get_native('pyelk.privateTraceReference')is alien,
 'privateNodeHasNoContainer':id(alien)not in state.json_parents}
expected=oracle['observation']
projected={key:expected[key]for key in actual}
for key in('imported','withNativeNestedLabel'):
    projected[key]={field:expected[key][field]for field in actual[key]}
comparison=diff(projected,actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceSha256':before,'oracleSha256':sha(oracle_path),
 'scope':'actual graph-element callback trace only; source EMF allTreeObjects/features remain raw observations, not an emulated runtime',
 'fullValidation':False,'wholeCoordinatorExecuted':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
