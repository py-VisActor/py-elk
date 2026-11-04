"""PRIVATE_SRC NEW_REPORT: actual internal-label writer bridge; no layout."""
import hashlib,json,sys
from pathlib import Path
source,out=map(Path,sys.argv[1:3]);sys.path.insert(0,str(source.resolve()))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
state=JsonLayoutSession({'id':'root','labels':[{'text':'label'}]})
label=state.graph['labels'][0];key='edgelabelcenterednessanalysis.includelabel'
assert not state.property_snapshot(label).has(key)
# An original host bridge keeps the real property ID and stored false presence.
state.set_stored_property(label,key,False)
snapshot=state.property_snapshot(label)
assert snapshot.has(key)and snapshot.get_native(key)is False
assert state.option(label,key,None)is False
assert 'org.eclipse.elk.'+key not in snapshot.values
state.set_stored_property(label,key,None)
assert not state.property_snapshot(label).has(key)
assert state.option(label,key,None)is None
state.set_stored_property(label,key,True)
assert state.property_snapshot(label).get_native(key)is True
# Sidecars belong to the assignment, not to an earlier value with the same key.
token=value_of_integer_box(9)
state.set_stored_property(label,'internal.count',9,integer_box=token)
assert state.property_snapshot(label).integer_boxes['internal.count']is token
state.set_stored_property(label,'internal.count',False)
assert 'internal.count'not in state.property_snapshot(label).integer_boxes
state.set_stored_property(label,'internal.count',None)
assert not state.property_snapshot(label).has('internal.count')
state.set_stored_property(label,'priority',9,integer_box=token)
assert state.integer_box_identity(label,'priority',None)is token
before=state.computed_options[id(label)].copy()
try:state.set_stored_property(label,'internal.count',8,integer_box=token)
except ValueError:pass
else:raise AssertionError('Mismatching assignment token accepted')
assert state.computed_options[id(label)]==before
try:state.set_stored_property({},key,True)
except ValueError:pass
else:raise AssertionError('Foreign holder accepted')
assert state.original=={'id':'root','labels':[{'text':'label'}]}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bindings={}
for m in tuple(sys.modules.values()):
    file=getattr(m,'__file__',None)
    if file:
        p=Path(file).resolve()
        if p.suffix=='.py'and p.is_relative_to(source.resolve()):bindings[p.relative_to(source.resolve()).as_posix()]=sha(p)
with out.open('x',encoding='utf8')as f:json.dump({'passed':True,'scope':'original-host internal stored-property bridge only',
 'sourceSha256':bindings,'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':True,'layoutExecuted':False}))
