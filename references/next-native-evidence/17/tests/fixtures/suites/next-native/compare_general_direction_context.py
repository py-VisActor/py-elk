"""PRIVATE_SRC REQUEST ORIGINAL REPORT; new typed GraphTransformer context."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,Insets,set_port_owner,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.native_adapters import _has_property,_read_property
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.directions_general import GraphTransformer
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
from pyelk.execution.node_micro import VectorChain
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads(original_path.read_bytes());request=json.loads(request_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path)and original['probeSha256']==sha(Path(__file__).with_name('general-direction-context-probe.cjs'))
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'DIRECTION':request['direction'],'DIRECTION_CONGRUENCY':request['congruency']})
g.size=Vec2(100.0,80.0);g.offset=Vec2(2.0,3.0)
n=LNode(g,properties=CanonicalPropertyMap());g.layerless_nodes.append(n);n.pos=Vec2(3.0,4.0);n.size=Vec2(20.0,10.0);n.padding=Insets(1.0,2.0,3.0,4.0)
ports=[]
for i,(index,side)in enumerate(zip(request['indices'],request['sides'])):
    p=LPort(properties=CanonicalPropertyMap());set_port_owner(p,n);p.size=Vec2(2.0,3.0);set_side(p,side);p.pos=Vec2(float(i+1),float(i+2));p.anchor=Vec2(.25,.75)
    p.properties.set_property('PORT_INDEX',index,integer_box=value_of_integer_box(index));ports.append(p)
edge=LEdge(properties=CanonicalPropertyMap());set_source(edge,ports[0]);set_target(edge,ports[1])
bend=Vec2(*map(float,request['bend']));edge.bend_points.append(bend)
junction=Vec2(*map(float,request['junction']));chain=VectorChain([junction]);edge.properties['JUNCTION_POINTS']=chain
presence=[_has_property(g,'NODE_LABELS_PADDING'),_has_property(n,'NODE_SIZE_MINIMUM')];events=[]
class Monitor:
    def begin(self,name,work):events.append(['begin',name,work])
    def done(self):events.append(['done'])
GraphTransformer(request['mode']).process(g,Monitor())
point=lambda v:[v.x,v.y]
insets=lambda v:[v.top,v.right,v.bottom,v.left]
number=lambda v:'-0'if v==0 and math.copysign(1,v)<0 else v
actual={'events':events,'graphSize':point(g.size),'graphOffset':point(g.offset),'nodePos':point(n.pos),'nodeSize':point(n.size),'nodePadding':insets(n.padding),
 'ports':[{'side':p.side,'pos':point(p.pos),'size':point(p.size),'anchor':point(p.anchor),'index':number(p.properties['PORT_INDEX'])}for p in ports],
 'zeroCached':ports[0].properties.integer_boxes['PORT_INDEX']is value_of_integer_box(0),'uncachedFresh':ports[1].properties.integer_boxes['PORT_INDEX']is not value_of_integer_box(-129),
 'typedChainSame':_read_property(edge,'JUNCTION_POINTS')is chain,'junctionSame':chain[0]is junction,'bendSame':edge.bend_points[0]is bend,'junction':point(junction),'bend':point(bend),
 'presenceBefore':presence,'presenceAfter':[_has_property(g,'NODE_LABELS_PADDING'),_has_property(n,'NODE_SIZE_MINIMUM')],'nodeMinimum':point(_read_property(n,'NODE_SIZE_MINIMUM')),'graphLabelPadding':insets(_read_property(g,'NODE_LABELS_PADDING')),
 'edgeLabelsSide':g.properties['EDGE_LABELS_SIDE_SELECTION'],'labelsEmpty':not n.labels and all(not p.labels for p in ports)and not edge.labels}
comparison=diff(original['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
