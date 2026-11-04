"""PRIVATE_SRC REQUEST ORIGINAL REPORT: only newly affected signed-zero leaf."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,set_port_owner
from pyelk.algorithms.layered.native_import import LLabel
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.label_side_selector import apply_dummy_side
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(request_path.read_bytes());o=json.loads(original_path.read_bytes())
assert o['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert o['requestSha256']==sha(request_path)and o['probeSha256']==sha(Path(__file__).with_name('label-selector-ceil-probe.cjs'))
g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'SPACING_EDGE_LABEL':r['spacing']})
n=LNode(g,type='LABEL',properties=CanonicalPropertyMap());n.size.y=float(r['height']);p=LPort(properties=CanonicalPropertyMap());set_port_owner(p,n)
e=LEdge(properties=CanonicalPropertyMap({'EDGE_THICKNESS':r['thickness']}));l=LLabel(None);l.properties=CanonicalPropertyMap({'EDGE_LABELS_INLINE':True});n.properties['ORIGIN']=e;n.properties['REPRESENTED_LABELS']=[l]
apply_dummy_side(n,'ABOVE');actual={'side':n.properties['LABEL_SIDE'],'portY':'-0'if p.pos.y==0 and math.copysign(1,p.pos.y)<0 else p.pos.y,'height':n.size.y}
c=diff(o['value'],actual,tolerant=False)
with out.open('x',encoding='utf8')as f:json.dump({'passed':c['passed'],'comparison':c,'actual':actual,'moduleSha256':sha(source/'pyelk/algorithms/layered/label_side_selector.py'),'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':c['passed'],'differences':len(c['differences'])}));raise SystemExit(0 if c['passed']else 1)
