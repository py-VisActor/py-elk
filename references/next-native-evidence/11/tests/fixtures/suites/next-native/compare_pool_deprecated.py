"""PRIVATE_SRC ORIGINAL NEW_REPORT; FIFO/direct-execution and per-element rules."""
import hashlib,json,sys
from pathlib import Path
source,oracle_path,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.pools import InstancePool,ProviderPools,NativeProvider,execute_algorithm
from pyelk.execution.resolver import AlgorithmDescriptor
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.diagnostics import BasicProgressMonitor
from pyelk.execution.deprecated import replace_deprecated_options
from pyelk.options.generic import RUNTIME_PROPERTY_SPECS
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
events=[]
class Factory:
    serial=0
    def create(self):
        self.serial+=1;value={'id':self.serial};events.append('create:'+str(self.serial));return value
    def destroy(self,value):events.append('destroy:'+str(value['id']))
pool=InstancePool(Factory());a,b=pool.fetch(),pool.fetch();pool.release(a);pool.release(b)
fifo=[pool.fetch()['id'],pool.fetch()['id']];pool.limit=0;pool.release(a)
pool.limit=1;pool.release(a);pool.release(b);fifo.append(pool.fetch()['id'])
pool.limit=-7;pool.release(a);pool.release(b);fifo.extend([pool.fetch()['id'],pool.fetch()['id']])
normal_events=[];failure=RuntimeError('layout fault');fetch_failure=RuntimeError('fetch fault')
class RealFactory:
    serial=0
    should_throw=False
    def create(self):
        self.serial+=1;serial=self.serial;provider=NativeProvider('org.eclipse.elk.fixed');real=provider.layout
        def observe(state,node,monitor):
            normal_events.append('layout:'+str(serial))
            if self.should_throw:raise failure
            return real(state,node,monitor)
        provider.layout=observe;normal_events.append('create:'+str(serial));return provider
    def destroy(self,provider):raise AssertionError('Unlimited actual pool unexpectedly destroyed provider')
data=AlgorithmDescriptor('org.eclipse.elk.fixed');same=AlgorithmDescriptor('org.eclipse.elk.fixed')
pools=ProviderPools();actual_pool=pools.pool_for(data);factory=RealFactory();actual_pool.factory=factory
state=JsonLayoutSession({'id':'r','children':[{'id':'n','x':5,'y':7,'width':10,'height':20}]})
monitor=BasicProgressMonitor();execute_algorithm(state,state.graph,data,monitor,pools);first=len(actual_pool.instances)
execute_algorithm(state,state.graph,data,BasicProgressMonitor(),pools);factory.should_throw=True;same_layout_failure=False
try:execute_algorithm(state,state.graph,data,BasicProgressMonitor(),pools)
except RuntimeError as error:same_layout_failure=error is failure
after_failure=len(actual_pool.instances);factory.should_throw=False
execute_algorithm(state,state.graph,data,BasicProgressMonitor(),pools)
class BadFactory:
    def create(self):raise fetch_failure
    def destroy(self,value):raise AssertionError('Unexpected destroy')
class BadPools:
    def pool_for(self,data):return InstancePool(BadFactory())
same_fetch_failure=False
try:execute_algorithm(state,state.graph,data,BasicProgressMonitor(),BadPools())
except RuntimeError as error:same_fetch_failure=error is fetch_failure
execution={'events':normal_events,'firstPoolSize':first,'afterFailure':after_failure,
 'sameLayoutFailure':same_layout_failure,'sameFetchFailure':same_fetch_failure,
 'dimensions':[state.graph['width'],state.graph['height']],'task':monitor.task_name,
 'childTasks':len(monitor._children),'distinctEqualIdPools':pools.pool_for(same)is not actual_pool}
legacy=JsonLayoutSession({'id':'legacy','layoutOptions':{'elk.portLabels.nextToPortIfPossible':False,
 'elk.nodeSize.options':'SPACE_EFFICIENT_PORT_LABELS'},'children':[{'id':'default'},
 {'id':'explicit','layoutOptions':{'elk.portLabels.placement':'INSIDE'}}]})
node=legacy.graph
def enum_values(holder,name):
    values=legacy.get_native_property(holder,name)
    return [value for value in RUNTIME_PROPERTY_SPECS['org.eclipse.elk.'+name].accepted_values if value in values]
def view(holder):
    return {'legacy':legacy.has_option(holder,'portLabels.nextToPortIfPossible'),
     'placementPresent':legacy.has_option(holder,'portLabels.placement'),'placement':enum_values(holder,'portLabels.placement'),
     'optionsPresent':legacy.has_option(holder,'nodeSize.options'),'options':enum_values(holder,'nodeSize.options')}
shared=legacy.get_native_property(node,'portLabels.placement');saved=set(shared)
try:
    initial=view(node);replace_deprecated_options(legacy,node)
    deprecated={'before':initial,'after':view(node),'defaultChild':view(node['children'][0]),
     'explicitChild':view(node['children'][1]),'sameShared':legacy.get_native_property(node,'portLabels.placement')is shared
       and legacy.get_native_property(node['children'][0],'portLabels.placement')is shared}
finally:shared.clear();shared.update(saved)
actual={'pool':{'events':events,'fifo':fifo},'execution':execution,'deprecated':deprecated}
oracle=json.loads(oracle_path.read_text('utf-8'));comparison=diff(oracle['observation'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceSha256':before,'oracleSha256':sha(oracle_path),'scope':'New pool/lifecycle with actual Fixed body plus per-element deprecated rules; not full traversal/coordinator',
 'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
