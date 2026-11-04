"""PRIVATE_SRC NEW_REPORT; validate only the explicit Integer token boundary."""
import hashlib,json,sys
from pathlib import Path
source,out=map(Path,sys.argv[1:3]);sys.path.insert(0,str(source.resolve()))
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.algorithms.layered.integer_box_tokens import IntegerBoxToken,value_of_integer_box
state=JsonLayoutSession({'id':'r'})
rejected=0
for value,token in ((True,value_of_integer_box(1)),(False,value_of_integer_box(0)),
                    (1.0,value_of_integer_box(1)),(1,IntegerBoxToken(True)),(2,value_of_integer_box(1))):
    try:state.set_option(state.graph,'priority',value,integer_box=token)
    except ValueError:rejected+=1
    else:raise AssertionError('Noninteger or mismatching payload accepted')
assert not state.has_option(state.graph,'priority')
token=value_of_integer_box(1);state.set_option(state.graph,'priority',1,integer_box=token)
assert state.integer_box_identity(state.graph,'priority',None)is token
assert type(state.get_native_property(state.graph,'priority'))is int
with out.open('x',encoding='utf-8')as f:json.dump({'passed':True,'negativeControls':rejected,'positiveControls':1,
 'scope':'explicit token setter payload guard only; no original reexecution',
 'sourceSha256':{p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*.py')},
 'fullValidation':False},f,indent=2)
