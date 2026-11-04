"""PRIVATE_SRC NEW_REPORT; actual owner scalar reads without default injection."""
import hashlib,json,sys
from pathlib import Path
source,out=map(Path,sys.argv[1:3]);sys.path.insert(0,str(source.resolve()))
from pyelk.execution.json_transfer import JsonLayoutSession
state=JsonLayoutSession({'id':'r'});root=state.graph
assert state.read_owner_scalar_property(root,'LayeredOptions','EDGE_ROUTING')=='ORTHOGONAL'
assert not state.has_option(root,'edgeRouting')
assert state.get_native_property(root,'edgeRouting')=='UNDEFINED'
assert state.read_owner_scalar_property(root,'LayeredOptions','RANDOM_SEED_0')==1
assert not state.has_option(root,'randomSeed') and state.get_native_property(root,'randomSeed')is None
assert state.read_owner_scalar_property(root,'LayeredOptions','CYCLE_BREAKING_STRATEGY_0')=='GREEDY'
assert not state.has_option(root,'layered.cycleBreaking.strategy')
try:state.read_owner_scalar_property(root,'LayeredOptions','NODE_SIZE_OPTIONS_1')
except ValueError:pass
else:raise AssertionError('Structured default silently constructed by the scalar bridge')
assert not state.has_option(root,'nodeSize.options')
configured=JsonLayoutSession({'id':'configured','layoutOptions':{'elk.edgeRouting':'POLYLINE','elk.randomSeed':99,
 'elk.layered.cycleBreaking.strategy':'SCC_NODE_TYPE'}})
for symbol,value in (('EDGE_ROUTING','POLYLINE'),('RANDOM_SEED_0',99),('CYCLE_BREAKING_STRATEGY_0','SCC_NODE_TYPE')):
    assert configured.read_owner_scalar_property(configured.graph,'LayeredOptions',symbol)==value
with out.open('x',encoding='utf-8')as f:json.dump({'passed':True,
 'scope':'explicit named owner scalar/default vs Core and stored override; structured defaults rejected; no runtime owner auto-selection',
 'sourceSha256':{p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*.py')},
 'layoutExecuted':False,'fullValidation':False},f,indent=2)
