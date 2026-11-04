from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.native_adapters import LLabelAdapter,LEdgeAdapter,LGraphAdapter
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,Insets,set_layer
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();label=SimpleNamespace(pos=Vec2(1,2),size=Vec2(3,4),id=0,properties={});adapter=LLabelAdapter(label);pos=adapter.pos;size=adapter.size;label.pos.x=17;live=adapter.pos.x
adapter.set_position(Vec2(8,9));adapter.set_size(Vec2(10,11));adapter.set_volatile_id(42)
label.properties['org.eclipse.elk.debugMode']=False
absent_before=adapter.has_property('TOPDOWN_LAYOUT');default_value=adapter.get_property('TOPDOWN_LAYOUT');absent_after=adapter.has_property('TOPDOWN_LAYOUT')
other=SimpleNamespace(pos=Vec2(),size=Vec2(),id=0,properties={});other_adapter=LLabelAdapter(other)
shared1=adapter.get_property('NODE_SIZE_OPTIONS');shared2=other_adapter.get_property('NODE_SIZE_OPTIONS')
edge=LEdge();edge.labels=[label];edge_adapter=LEdgeAdapter(edge);edge_labels=edge_adapter.labels;edge.labels.append(other);label.size.x=99
g=LGraph(None,None,None);layer=Layer(g);g.layers.append(layer);a=LNode(g);b=LNode(g);comment=LNode(g)
set_layer(a,layer);set_layer(b,layer);a.id=0;b.id=1;comment.id=20;b.type='LONG_EDGE';a.labels=[];b.labels=[];comment.labels=[]
a.properties['TOP_COMMENTS']=[comment,comment];a.properties['BOTTOM_COMMENTS']=[comment];b.properties['TOP_COMMENTS']=[comment]
calls=[]
def accepted(node):calls.append(node.id);return node.type=='NORMAL'
graph_adapter=LGraphAdapter(g,True,True,accepted);node_views=graph_adapter.nodes;node=node_views[0];first_ports=node.ports
new_port=LPort(a);a.ports.append(new_port);old_margin=a.margin;old_padding=a.padding;margin1=node.margin;margin2=node.margin;margin1.top=999;no_mutation=a.margin.top
node.margin=Insets(1,2,3,4);node.padding=Insets(5,6,7,8);node.id=81
third=LNode(g);set_layer(third,layer);gsize=graph_adapter.size;graph_adapter.size=Vec2(31,32);graph_adapter.id=37
unsupported=False;raw_error=None
try:graph_adapter.get_position()
except NotImplementedError as e:unsupported=True;raw_error={'name':type(e).__name__,'message':str(e)}
vector=lambda v:[v.x,v.y];spacing=lambda v:[v.top,v.right,v.bottom,v.left]
actual={'shape':{'live':live,'position':vector(pos),'size':vector(size),'positionSame':pos is adapter.pos,'sizeSame':size is adapter.size,'id':label.id,'storedFalse':adapter.get_property('DEBUG_MODE'),'hasStoredFalse':adapter.has_property('DEBUG_MODE'),'absentBefore':absent_before,'defaultValue':default_value,'absentAfter':absent_after,'sharedEnumDefault':shared1 is shared2,'sharedDefaultHas':[adapter.has_property('NODE_SIZE_OPTIONS'),other_adapter.has_property('NODE_SIZE_OPTIONS')]},
        'edge':{'physicalLabels':len(edge.labels),'cachedLabels':len(edge_labels),'sameList':edge_labels is edge_adapter.labels,'liveFirstWidth':edge_labels[0].size.x},
        'graph':{'cachedNodes':len(node_views),'sameList':node_views is graph_adapter.nodes,'filterCalls':calls,'sourceNodeKinds':['a'if n.element is a else'comment'for n in node_views],
                 'commentsDistinct':node_views[1]is not node_views[2]and node_views[2]is not node_views[3],'commentSameElement':node_views[1].element is node_views[3].element,'nsFlags':[n.transparent_north_south_edges for n in node_views],'parentSame':all(n.graph is graph_adapter for n in node_views),'emptyEdgesSame':node.incoming_edges is node.outgoing_edges,
                 'cachedPorts':len(node.ports),'portsSameList':first_ports is node.ports,'marginFresh':margin1 is not margin2 and margin1 is not old_margin,'marginMutationDidNotApply':no_mutation,'marginSame':old_margin is a.margin,'margin':spacing(a.margin),'paddingSame':old_padding is a.padding,'padding':spacing(a.padding),'nodeId':a.id,'sizeSame':gsize is graph_adapter.size,'size':vector(gsize),'graphId':g.id,'unsupportedPosition':unsupported}}
raw=json.loads(original.read_text(encoding='utf8'));assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
comparison=diff(raw['value'],actual);after=hashes();assert before==after
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'sourceRawError':raw['rawError'],'nativeRawError':raw_error,'rawErrorParity':False,
        'scope':'Only approved shape/edge/label/graph/node foundation views, scalar/shared EnumSet defaults, actual cache identity and geometry; no Port/margin/calculator/full pipeline claim'}
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
