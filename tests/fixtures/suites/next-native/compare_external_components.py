"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; changed external component paths."""
import hashlib,json,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_port_owner,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.components_general import ComponentsProcessor
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.global_properties import parse_global_mapping
from pyelk.execution.node_micro import _native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
request=json.loads(request_path.read_text('utf-8'));original=json.loads(original_path.read_text('utf-8'))
assert sha(request_path)==original['requestSha256'];metadata=NativeMetadataService(['layered'])
point=lambda p:[p.x,p.y]
order=('UNDEFINED','NORTH','EAST','SOUTH','WEST');actual=[]
for case in request['cases']:
    graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap()
    graph.properties.update({k:_native(v)for k,v in parse_global_mapping(case['options'],metadata=metadata).items()})
    graph.properties['GRAPH_PROPERTIES']={'EXTERNAL_PORTS'}
    nodes=[]
    def make():
        n=LNode(graph);n.labels=[];n.properties=CanonicalPropertyMap();nodes.append(n);graph.layerless_nodes.append(n)
        n.pos=Vec2(len(nodes)/4,-len(nodes)/2);return n
    def port(n):
        p=LPort();p.labels=[];p.properties=CanonicalPropertyMap();set_port_owner(p,n);return p
    for i,sides in enumerate(case['sides']):
        n=make();p=port(n);value=len(case['sides'])-i
        n.properties.set_property('MODEL_ORDER',value,integer_box=value_of_integer_box(value))
        for side in sides:
            ext=make();ext.type='EXTERNAL_PORT';ext.properties['EXT_PORT_SIDE']=side;ep=port(ext)
            edge=LEdge();edge.labels=[];edge.properties=CanonicalPropertyMap();set_source(edge,p);set_target(edge,ep)
    processor=ComponentsProcessor();parts=processor.split(graph)
    for i,h in enumerate(parts):h.size=Vec2(11.5+3*i,7+2.25*i);h.offset=Vec2(.25*i-1,-.75*i)
    split=[{'nodes':[nodes.index(n)for n in h.layerless_nodes],
      'sides':sorted(h.properties['EXT_PORT_CONNECTIONS'],key=order.index)}for h in parts]
    processor.combine(parts,graph);placer=processor.graph_placer
    groups=None
    if hasattr(placer,'component_groups'):
        groups=[{'values':[parts.index(h)for h in group.values()],
                 'keys':[sorted(key,key=order.index)for key in group.components.keys()],
                 'componentOrder':[parts.index(h)for h in group.component_order]if hasattr(group,'component_order')else None}
                for group in placer.component_groups]
    actual.append({'name':case['name'],'split':split,'size':point(graph.size),
      'nodes':[{'id':nodes.index(n),'pos':point(n.pos),'targetOwner':n.graph is graph}for n in graph.layerless_nodes],
      'groups':groups})
comparison=diff(original['observation'],actual,tolerant=False)
bindings={}
for module in tuple(sys.modules.values()):
    file=getattr(module,'__file__',None)
    if file:
        p=Path(file).resolve()
        if p.suffix=='.py'and p.is_relative_to(source.resolve()):bindings[p.relative_to(source.resolve()).as_posix()]=sha(p)
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceSha256':bindings,
 'oracleSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
 'originalReexecuted':False,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
