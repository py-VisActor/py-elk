"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; new Integer provenance witness."""
import hashlib,json,os,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box,new_integer_box
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert sha(request_path)==oracle['requestSha256']
state=JsonLayoutSession(request['graph'],request['globalOptions']);root=state.graph
a,b,c,d,e=root['children'];port=a['ports'][0]
get=lambda n:state.integer_box_identity(n,'priority',None)
group='layered.considerModelOrder.groupModelOrder.crossingMinimizationId';zero=value_of_integer_box(0)
actual={'localLargeDistinct':get(a)is not get(b),'localSmallShared':get(c)is get(d),
 'globalShared':get(root)is get(e),'localOverridesGlobal':get(a)is not get(root),
 'portGlobalAbsent':not state.has_option(port,'priority'),'numericPayloads':[state.option(n,'priority')for n in(a,c,e)],
 'defaultZeroShared':state.integer_box_identity(a,group,zero)is zero,'defaultAbsent':not state.has_option(a,group)}
snapshot=state.property_snapshot(a);copied=snapshot.copy();actual['copyTokenShared']=copied.integer_boxes['priority']is get(a)
state.set_option(a,'priority',0,integer_box=new_integer_box(0))
actual['directNewDistinct']=get(a)is not zero;actual['copyIndependent']=copied.get_native('priority')==129
state.remove_option(a,'priority');actual['removedAbsent']=not state.has_option(a,'priority')
assert 'priority'not in state.property_snapshot(a).integer_boxes
state.set_option(a,'priority',129)
try:get(a)
except TypeError:pass
else:raise AssertionError('Numeric assignment inferred an Integer identity')
assert 'priority'not in state.property_snapshot(a).integer_boxes
comparison=diff(oracle['observation'],actual)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceSha256':before,'oracleSha256':sha(oracle_path),'pid':os.getpid(),'parentPid':os.getppid(),'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
