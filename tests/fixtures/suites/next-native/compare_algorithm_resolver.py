"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT; per-node resolver and diagnostic message."""
import hashlib,json,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.resolver import AlgorithmRegistry,visit_algorithm
from pyelk._errors import ValidationError,UnsupportedAlgorithmError
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));oracle=json.loads(oracle_path.read_text('utf-8'))
assert sha(request_path)==oracle['requestSha256']
registry=AlgorithmRegistry();lookups=[]
for identifier in request['lookups']:
    data=registry.lookup(identifier)
    lookups.append({'id':identifier,'resolved':data.id if data else None,'cachedIdentity':not data or data is registry.lookup(identifier)})
cases=[];native_errors=[]
for case in request['cases']:
    state=JsonLayoutSession(case['graph']);node=state.graph
    for index in case.get('select',[]):node=node['children'][index]
    if case.get('presetResolved'):state.set_option(node,'resolvedAlgorithm',registry.lookup(case['presetResolved']))
    outcome='returned';message=None
    try:visit_algorithm(state,node,registry)
    except ValidationError as error:
        outcome='threw';message=error.message
        native_errors.append({'id':case['id'],'pythonCategory':type(error).__name__,'code':error.code,'path':error.path,'displayText':str(error)})
    data=state.get_native_property(node,'resolvedAlgorithm')
    cases.append({'id':case['id'],'outcome':outcome,'message':message,'resolved':data.id if data else None,
                  'hasResolved':state.has_option(node,'resolvedAlgorithm'),'registryIdentity':not data or data is registry.lookup(data.id)})
actual={'lookups':lookups,'cases':cases};comparison=diff(oracle['observation'],actual)
# Separate registered-service controls; no constructor/worker loading claim.
assert AlgorithmRegistry(['one.shared','two.shared']).lookup('shared')is None
empty=AlgorithmRegistry([]);state=JsonLayoutSession({'id':'missing-default','children':[{'id':'n'}]})
try:visit_algorithm(state,state.graph,empty)
except UnsupportedAlgorithmError as error:
    assert 'Unable to load default layout algorithm org.eclipse.elk.layered'in error.message
else:raise AssertionError('Unregistered default algorithm silently resolved')
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'nativeHostErrors':native_errors,'sourceSha256':before,'oracleSha256':sha(oracle_path),
 'scope':'13 per-node visitor cases and 7 suffix lookups; native error.message matches original diagnostic, Python categories/display retained separately',
 'wholeVisitorTraversal':False,'constructorRegistrySelection':False,'recursiveCoordinator':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
