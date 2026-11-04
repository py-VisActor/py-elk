"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; one actual stored-map copy witness."""
import hashlib
import json
import os
from pathlib import Path
import sys

source,request_path,oracle_path,output_path=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import pyelk
from layout_checks import diff
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.node_micro import _PropertyReader

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert sha(request_path)==oracle['requestSha256']
state=JsonLayoutSession(request['graph'],request['globalOptions']);a,b=state.graph['children'];reader=_PropertyReader(state)
minimum=reader.get(a,'node','nodeSize.minimum');padding=reader.get(a,'node','nodeLabels.padding')
constraints=reader.get(a,'node','nodeSize.constraints');reader.get(a,'node','direction')
scalar_absent=not state.has_option(a,'direction')
state.computed_options.setdefault(id(a),{})['private.scalar']=42.0
algorithm={'native':'opaque algorithm data'};state.set_option(a,'resolvedAlgorithm',algorithm)
snapshot=state.property_snapshot(a);copied=snapshot.copy()
value={'minimumShared':copied.get_native('nodeSize.minimum') is minimum,
       'paddingShared':copied.get_native('nodeLabels.padding') is padding,
       'constraintsShared':copied.get_native('nodeSize.constraints') is constraints,
       'algorithmShared':copied.get_native('resolvedAlgorithm') is algorithm,
       'scalarAbsentBefore':scalar_absent,'scalarAbsentAfter':not copied.has('direction'),
       'privateValue':copied.get('private.scalar'),
       'individualShared':copied.get_native('spacing.individual') is reader.get(a,'node','spacing.individual')}
minimum.x=99;value['mutationVisible']=copied.get_native('nodeSize.minimum').x==99
state.set_option(a,'priority',8)
value['copiedKeyIndependent']=copied.get('priority')==7 and state.option(a,'priority')==8
state.set_option(a,'nodeSize.minimum',{'x':1,'y':2})
value['replacementIndependent']=(copied.get_native('nodeSize.minimum')is minimum
                                 and reader.get(a,'node','nodeSize.minimum')is not minimum)
assert copied.has('org.eclipse.elk.priority')and copied.get('elk.priority')==7
assert copied.get('direction','caller-default')=='caller-default'
copied.set('private.scalar',None);assert not copied.has('private.scalar')and snapshot.has('private.scalar')
copied.set('aspectRatio',2**53+1);assert type(copied.get_native('aspectRatio'))is float and copied.get_native('aspectRatio')==2**53
assert state.option(a,'aspectRatio','none')=='none'
state.remove_option(a,'nodeSize.options')
assert not state.property_snapshot(a).has('nodeSize.options')
assert state.original==request['graph']and state.options==request['globalOptions']
try:state.property_snapshot({'id':'foreign'})
except ValueError:pass
else:raise AssertionError('Snapshot accepted a foreign holder')
comparison=diff(oracle['observation'],value)
after={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')};assert before==after
report={'passed':comparison['passed'],'difference':comparison,'actual':value,'expected':oracle['observation'],
        'pid':os.getpid(),'parentPid':os.getppid(),'python':sys.executable,'modulePath':str(Path(pyelk.__file__).resolve()),
        'sourceBeforeSha256':before,'sourceAfterSha256':after,'requestSha256':sha(request_path),'oracleSha256':sha(oracle_path),
        'comparatorSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False,
        'scope':'Actual stored native typed values only; no public API, geometry/ID clone, or unproduced integer identity promise'}
with output_path.open('x',encoding='utf-8')as out:json.dump(report,out,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
