"""PRIVATE_SRC REQUEST ORIGINAL REPORT; only new actual Property default leaves."""
import hashlib,json,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,set_port_owner
from pyelk.algorithms.layered.directions_general import GraphTransformer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap,canonical_property_key
from pyelk.algorithms.layered.native_adapters import _has_property,_read_property
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads(original_path.read_bytes());assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path)and original['probeSha256']==sha(Path(__file__).with_name('general-direction-default-probe.cjs'))
actual=[]
for physical_null in(False,True):
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'DIRECTION':'DOWN','DIRECTION_CONGRUENCY':'READING_DIRECTION'})
    n=LNode(g,type='EXTERNAL_PORT',properties=CanonicalPropertyMap());g.layerless_nodes.append(n)
    p=LPort(properties=CanonicalPropertyMap());set_port_owner(p,n)
    if physical_null:n.properties._values[canonical_property_key('EXT_PORT_SIDE')]=None
    p.properties._values[canonical_property_key('PORT_INDEX')]=None
    before=[_has_property(n,'EXT_PORT_SIDE'),_has_property(p,'PORT_INDEX')];events=[]
    class Monitor:
        def begin(self,name,work):events.append(['begin',name,work])
        def done(self):events.append(['done'])
    GraphTransformer('TO_INTERNAL_LTR').process(g,Monitor())
    actual.append({'physicalNull':physical_null,'before':before,'after':[_has_property(n,'EXT_PORT_SIDE'),_has_property(p,'PORT_INDEX')],'side':_read_property(n,'EXT_PORT_SIDE'),'indexNullish':_read_property(p,'PORT_INDEX')is None,'events':events})
comparison=diff(original['value'],actual,tolerant=False)
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':{p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')},'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
