"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; actual cleanup/resize only."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,Layer,Vec2,Insets,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.native_adapters import _has_property,_read_property
from pyelk.algorithms.layered.resize_general import clear_layers,resize_graph
from pyelk.execution.global_properties import parse_global_mapping
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.node_micro import _native
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
request=json.loads(request_path.read_text('utf-8'));original=json.loads(original_path.read_text('utf-8'))
assert sha(request_path)==original['requestSha256']
metadata=NativeMetadataService(['layered'])
def number(v):return 'NaN'if math.isnan(v)else '-0'if v==0 and math.copysign(1,v)<0 else v
def point(v):return [number(v.x),number(v.y)]
actual=[]
for case in request['cases']:
    graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap()
    graph.size=Vec2(*case['size']);graph.offset=Vec2(*case['offset']);graph.padding=Insets(*case['padding'])
    graph.properties.update({k:_native(v)for k,v in parse_global_mapping(case['options'],metadata=metadata).items()})
    nodes=[];layers=[]
    for i,side in enumerate(('UNDEFINED','WEST','EAST','NORTH','SOUTH')):
        n=LNode(graph);n.properties=CanonicalPropertyMap();n.id=i;n.pos=Vec2(i-2,i+1);nodes.append(n)
        if i:n.type='EXTERNAL_PORT';n.properties['EXT_PORT_SIDE']=side
        if i<2:graph.layerless_nodes.append(n)
        else:
            layer=Layer(graph);layers.append(layer);graph.layers.append(layer);set_layer(n,layer,0)
    if case.get('external'):graph.properties['GRAPH_PROPERTIES']={'EXTERNAL_PORTS'}
    before_minimum=_has_property(graph,'NODE_SIZE_MINIMUM');size=graph.size;offset=graph.offset
    graph.properties['PROCESSORS']=[];clear_layers(graph);resize_graph(graph)
    minimum=_read_property(graph,'NODE_SIZE_MINIMUM')if _has_property(graph,'NODE_SIZE_MINIMUM')else None
    actual.append({'name':case['name'],'size':point(graph.size),'offset':point(graph.offset),'sameSize':size is graph.size,'sameOffset':offset is graph.offset,
      'minimumBefore':before_minimum,'minimumAfter':_has_property(graph,'NODE_SIZE_MINIMUM'),'minimum':point(minimum)if minimum is not None else None,
      'nodes':[{'id':n.id,'pos':point(n.pos),'layerNull':n.layer is None}for n in graph.layerless_nodes],
      'layers':len(graph.layers),'oldLayerNodeCounts':[len(l.nodes)for l in layers]})
comparison=diff(original['observation'],actual,tolerant=False)
bindings={}
for module in tuple(sys.modules.values()):
    file=getattr(module,'__file__',None)
    if file:
        p=Path(file).resolve()
        if p.suffix=='.py'and p.is_relative_to(source.resolve()):bindings[p.relative_to(source.resolve()).as_posix()]=sha(p)
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceSha256':bindings,
 'requestSha256':sha(request_path),'oracleSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),
 'fullLayoutExecuted':False,'actualCleanupAndResizeExecuted':True,'originalReexecuted':False,'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
