"""PRIVATE_SRC REQUEST SAVED_ORIGINAL NEW_REPORT; real full coordinator trace."""
import copy,hashlib,json,sys
from pathlib import Path
source,request_path,oracle_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from layout_checks import diff
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.diagnostics import BasicProgressMonitor
from pyelk.execution import recursive
from pyelk.execution.pools import InstancePool
from recursive_observations import without_generated_hashes
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_text('utf-8'));saved=copy.deepcopy(request)
oracle=json.loads(oracle_path.read_text('utf-8'));assert sha(request_path)==oracle['requestSha256']
metadata=None
if 'algorithms'in request:
    from pyelk.execution.metadata_service import NativeMetadataService
    metadata=NativeMetadataService(request['algorithms'])
kwargs={}if metadata is None else {'metadata':metadata}
state=JsonLayoutSession(request.get('graph',request),**kwargs);root=state.graph
engine=recursive.RecursiveLayoutEngine(**kwargs);events=[];providers={};recursion=[];executing=[]
def properties():
    result=[]
    for name in request.get('observeProperties',()):
        has=state.has_option(root,name)
        result.append({'id':name,'has':has,'value':state.get_native_property(root,name)if has else None})
    return result
before_properties=properties()
pool_names={id(engine.pools.pool_for(engine.registry.lookup(name))):name for name in request.get('observePools',())}
used_pools={}
setup=request.get('nativeOnlySetup')
if setup and setup.get('rootResolvedAlgorithm'):
    descriptor=engine.registry.lookup(setup['rootResolvedAlgorithm'])
    assert descriptor is not None
    state.set_option(root,'resolvedAlgorithm',descriptor)
def geometry(node):return {key:node[key]for key in('id','x','y','width','height')}
def token(provider):
    if id(provider)not in providers:providers[id(provider)]=(provider,len(providers)+1)
    return providers[id(provider)][1]
saved_node=engine._node;saved_execute=recursive.execute_algorithm
saved_fetch=InstancePool.fetch;saved_release=InstancePool.release
def tracked_node(current,node,monitor):
    recursion.append(node['id']);events.append({'kind':'enter','node':node['id'],'geometry':geometry(node)})
    try:return(yield from saved_node(current,node,monitor))
    finally:
        events.append({'kind':'leave','node':node['id'],'geometry':geometry(node)});recursion.pop()
def tracked_execute(current,node,descriptor,monitor,pools):
    events.append({'kind':'execute','node':node['id'],'geometry':geometry(node)});executing.append(node['id'])
    try:return saved_execute(current,node,descriptor,monitor,pools)
    finally:executing.pop()
def tracked_fetch(pool):
    count=len(pool.instances);provider=saved_fetch(pool)
    event={'kind':'fetch','node':recursion[-1]if recursion else None,
      'execution':executing[-1]if executing else None,'before':count,'after':len(pool.instances),'provider':token(provider)}
    if pool_names:
        assert id(pool)in pool_names,'Unexpected actual provider pool'
        used_pools.setdefault(id(pool),pool);event['algorithm']=pool_names[id(pool)]
    events.append(event)
    return provider
def tracked_release(pool,provider):
    count=len(pool.instances);result=saved_release(pool,provider)
    event={'kind':'release','execution':executing[-1]if executing else None,
      'before':count,'after':len(pool.instances),'provider':token(provider)}
    if pool_names:event['algorithm']=pool_names[id(pool)]
    events.append(event)
    return result
engine._node=tracked_node;recursive.execute_algorithm=tracked_execute
InstancePool.fetch=tracked_fetch;InstancePool.release=tracked_release
monitor=BasicProgressMonitor()
try:engine.layout(state,monitor=monitor)
finally:
    recursive.execute_algorithm=saved_execute;InstancePool.fetch=saved_fetch;InstancePool.release=saved_release
pool=engine.pools.pool_for(state.get_native_property(root,'resolvedAlgorithm'))
actual={'result':state.export(),'events':events,'providerCount':len(providers),
 'queuedProviders':[token(provider)for provider in pool.instances],
 'geometry':[geometry(node)for node in state.nodes],
 'scaleFactors':[[node['id'],state.get_native_property(node,'topdown.scaleFactor')]for node in state.nodes],
 'monitor':{'name':monitor.task_name,'closed':monitor._closed},'layoutExecuted':True}
if 'descriptors'in oracle['observation']:
    actual['nativeOnlySetup']=setup
    actual['descriptors']=[{'id':node['id'],'present':state.has_option(node,'resolvedAlgorithm'),
      'algorithm':state.get_native_property(node,'resolvedAlgorithm').id if state.has_option(node,'resolvedAlgorithm')else None,
      'hierarchy':state.get_native_property(node,'hierarchyHandling')}for node in state.nodes]
if 'pools'in oracle['observation']:
    actual['pools']=[{'algorithm':pool_names[key],
      'fetches':sum(e['kind']=='fetch'and e.get('algorithm')==pool_names[key]for e in events),
      'releases':sum(e['kind']=='release'and e.get('algorithm')==pool_names[key]for e in events),
      'queued':[token(provider)for provider in value.instances]}for key,value in used_pools.items()]
if 'beforeProperties'in oracle['observation']:
    assert state.metadata_service is engine.metadata_service is metadata
    assert state._algorithm_registry is metadata.registry and state._provider_pools is metadata.pools
    actual['beforeProperties']=before_properties;actual['afterProperties']=properties()
    actual['metadata']={kind:getattr(metadata,kind)()for kind in('algorithms','options','categories')}
# Only generated integer hashes on actual imported graph elements are removed.
# User fields and hashes in arbitrary nested business dictionaries remain.
owned_inputs={'/result'+state.paths[key]:state.origins[key]for key in state.kinds}
comparison=diff(without_generated_hashes(oracle['observation'],owned_inputs),actual,tolerant=False)
assert request==saved
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,
 'actual':actual,'sourceSha256':before,'oracleSha256':sha(oracle_path),'checkerSha256':sha(Path(__file__)),
 'originalReexecuted':False,'fullCoordinatorExecuted':True,'publicAPIIntegrated':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
