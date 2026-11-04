"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: new recursive/registry Layered caller."""
import copy,hashlib,json,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.recursive import RecursiveLayoutEngine
from pyelk.execution.diagnostics import BasicProgressMonitor
from pyelk.algorithms.layered.provider import LayeredProvider
from pyelk.execution.pools import NativeProviderFactory
from layout_checks import diff,_project_reference_shape_hashes
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_bytes());original=json.loads(original_path.read_bytes())
assert original['requestSha256']==sha(request_path)and original['outcome']=='returned'
saved=copy.deepcopy(request['graph']);metadata=NativeMetadataService(request['constructor']['algorithms'])
state=JsonLayoutSession(request['graph'],metadata=metadata);engine=RecursiveLayoutEngine(metadata=metadata)
monitor=BasicProgressMonitor(logging=request['layoutArguments']['logging'],measure_execution_time=False)
engine.layout(state,monitor=monitor)
result=state.export();result['logging']=monitor.collect()
with out.with_name('result.json').open('x',encoding='utf8')as f:json.dump(result,f,indent=2)
assert request['graph']==saved
assert state._algorithm_registry is metadata.registry is engine.registry
assert state._provider_pools is metadata.pools is engine.pools
descriptor=metadata.lookup_algorithm('layered');pool=metadata.pools.pool_for(descriptor)
assert len(pool.instances)==1
provider=pool.instances[0];assert isinstance(provider.body,LayeredProvider)
config=provider.body.graph_configurator;assembler=config.algorithm_assembler
cache=assembler.cache.copy();assert cache
# Fetch/release verifies lifetime without repeating the successful mathematics.
assert pool.fetch()is provider
assert provider.body.graph_configurator is config
assert all(assembler.cache[key]is value for key,value in cache.items())
pool.release(provider)
another=NativeProviderFactory(descriptor.id).create()
assert isinstance(another.body,LayeredProvider)and another.body is not provider.body
assert another.body.graph_configurator is not config
assert another.body.graph_configurator.algorithm_assembler.cache=={}
raw=diff(original['result'],result,tolerant=False)
reference=copy.deepcopy(original['result']);adaptations=[];violations=[]
_project_reference_shape_hashes(saved,reference,result,prefix='',adaptations=adaptations,violations=violations)
comparison=diff(reference,result,tolerant=False)
passed=comparison['passed']and not violations
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf8')as f:json.dump({'passed':passed,'rawStrict':raw,'comparison':comparison,
 'adaptations':adaptations,'violations':violations,'result':result,'candidateInputPreserved':True,
 'registeredPrivateLayeredBodyInvoked':True,'recursiveEngineInvoked':True,'sameMetadataRegistryAndPools':True,
 'realPersistentOwnerAndCachedProcessorReuse':True,'freshFactoryGetsDistinctOwner':True,
 'nativeLayoutExecutions':1,'poolLifetimeControlsExecuteNoAdditionalLayout':True,'referenceExecutions':0,
 'publicPackageIntegrated':False,'wholeAlgorithmAccepted':False,'fullValidation':False,
 'requestSha256':sha(request_path),'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),
 'sourceFilesSha256':before,'sourceTreeUnchanged':True},f,indent=2)
print(json.dumps({'passed':passed,'rawStrictPassed':raw['passed'],'rawDifferences':len(raw['differences']),
                  'strictDifferencesAfterExistingProjection':len(comparison['differences']),'violations':violations}))
raise SystemExit(0 if passed else 1)
