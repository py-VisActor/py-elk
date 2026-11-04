"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; general split/SimpleRow delta."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,Insets,set_source,set_target,set_port_owner
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.components_general import ComponentsProcessor
from pyelk.algorithms.layered.native_adapters import _read_property,_has_property
from pyelk.algorithms.layered.integer_box_tokens import value_of_integer_box
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.execution.global_properties import parse_global_mapping
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.node_micro import _native
from pyelk.options.generic import RUNTIME_PROPERTY_SPECS
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
request=json.loads(request_path.read_text('utf-8'));original=json.loads(original_path.read_text('utf-8'))
assert sha(request_path)==original['requestSha256'];metadata=NativeMetadataService(['layered'])
point=lambda v:[v.x,v.y]
actual=[]
for case in request['cases']:
    graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap()
    for name,value in parse_global_mapping(case['options'],metadata=metadata).items():
        graph.properties[name]=_native(value)
        if RUNTIME_PROPERTY_SPECS[name].kind=='integer':graph.properties.integer_boxes[name]=value_of_integer_box(value)
    random=JavaRandom(7);processors=[];graph.random=random;graph.properties['RANDOM']=random;graph.properties['PROCESSORS']=processors
    session=SimpleNamespace();graph._source_session=session;graph.padding=Insets(1,2,3,4)
    nodes=[];ports=[];edges=[]
    for i,row in enumerate(case['nodes']):
        n=LNode(graph);n.properties=CanonicalPropertyMap();n.id=i;n.pos=Vec2(i,-i);n.size=Vec2(10+i,20+i)
        for key,field in(('PRIORITY','priority'),('MODEL_ORDER','order')):
            if field in row:n.properties.set_property(key,row[field],integer_box=value_of_integer_box(row[field]))
        nodes.append(n);graph.layerless_nodes.append(n);current=[]
        for unused in range(row.get('ports',1)):
            p=LPort();set_port_owner(p,n);current.append(p)
        ports.append(current)
    for i,(a,b,c,d)in enumerate(case['edges']):
        edge=LEdge();edge.properties=CanonicalPropertyMap();edge.id=i;set_source(edge,ports[a][b]);set_target(edge,ports[c][d])
        edge.bend_points.append(Vec2(i+1,i+2));edge.labels=[SimpleNamespace(pos=Vec2(i+3,i+4))];edges.append(edge)
    if case['external']:graph.properties['GRAPH_PROPERTIES']={'EXTERNAL_PORTS'}
    original_minimum=graph.properties.get('NODE_SIZE_MINIMUM');seed=graph.properties.integer_boxes['randomSeed']
    processor=ComponentsProcessor();components=processor.split(graph)
    split=[]
    for h in components:
        assert h._source_session is session and h.random is random
        split.append({'nodeOrder':[nodes.index(n)for n in h.layerless_nodes],'sameGraph':h is graph,'paddingSame':h.padding is graph.padding,
          'minimumPresent':_has_property(h,'NODE_SIZE_MINIMUM'),'integerBoxShared':h.properties.integer_boxes['randomSeed']is seed,
          'randomShared':h.properties['RANDOM']is random,'processorsShared':h.properties['PROCESSORS']is processors,
          'nodeOwners':all(n.graph is h for n in h.layerless_nodes),
          'externalConnections':sorted(h.properties['EXT_PORT_CONNECTIONS'])if _has_property(h,'EXT_PORT_CONNECTIONS')else None})
    for i,h in enumerate(components):h.size=Vec2(20+15*i,10+5*i);h.offset=Vec2(i-1,2-i)
    processor.combine(components,graph)
    actual.append({'name':case['name'],'split':split,'componentOrderAfterCombine':[[nodes.index(n)for n in h.layerless_nodes]for h in components],
      'targetNodes':[{'index':nodes.index(n),'pos':point(n.pos),'targetOwner':n.graph is graph}for n in graph.layerless_nodes],
      'edgeBends':[[point(p)for p in e.bend_points]for e in edges],'edgeLabels':[[point(l.pos)for l in e.labels]for e in edges],
      'junctionPresence':[_has_property(e,'JUNCTION_POINTS')for e in edges],'size':point(graph.size),
      'minimumRetained':_read_property(graph,'NODE_SIZE_MINIMUM')is original_minimum if original_minimum is not None else None,
      'randomShared':graph.properties['RANDOM']is random,'processorsShared':graph.properties['PROCESSORS']is processors})
comparison=diff(original['observation'],actual,tolerant=False)
bindings={}
for module in tuple(sys.modules.values()):
    file=getattr(module,'__file__',None)
    if file:
        p=Path(file).resolve()
        if p.suffix=='.py'and p.is_relative_to(source.resolve()):bindings[p.relative_to(source.resolve()).as_posix()]=sha(p)
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceSha256':bindings,
 'oracleSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
 'originalReexecuted':False,'fullLayoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
