"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: new real full compactor caller."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
selected=[int(v)for v in sys.argv[5:]]
from layout_checks import diff
from pyelk.algorithms.layered import connected_compactor as cc
from pyelk.algorithms.layered.component_groups import ComponentGroupGraphPlacer,ComponentGroupModelOrderGraphPlacer,ModelOrderRowGraphPlacer
from pyelk.algorithms.layered.graph import LGraph,LNode,LEdge,LPort,Vec2,Insets,set_port_owner,set_source,set_target
from pyelk.algorithms.layered.native_import import LLabel
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.native_adapters import _has_property,_read_property
from pyelk.algorithms.layered.ports import set_side
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_bytes());original=json.loads(original_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path) and original['probeSha256']==sha(Path(__file__).with_name('placer-compaction-probe.cjs'))
assert original['actualPlacerConsumer'] is True and original['actualConnectedCompactor'] is True and original['inputGeometryExplicitlySupplied'] is True and original['layoutExecuted'] is False
def number(v):return 'NaN'if math.isnan(v)else('Infinity'if v>0 else'-Infinity')if not math.isfinite(v)else'-0'if v==0 and math.copysign(1,v)<0 else v
def point(v):return [number(v.x),number(v.y)]
def box(v):return list(map(number,(v.x,v.y,v.width,v.height)))
actual=[]
selected=list(range(len(request['cases'])))if not selected else selected
assert len(selected)==len(set(selected)) and all(0<=i<len(request['cases'])for i in selected)
for c in (request['cases'][i]for i in selected):
    graphs=[];original_nodes=[];refs=[];original_edges=[]
    for inputs in c['graphs']:
        g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'EXT_PORT_CONNECTIONS':set(inputs['sides'])});g.size=Vec2(*map(float,inputs['layoutSize']));g.offset=Vec2(*map(float,inputs['layoutOffset']));g.properties.update({'ASPECT_RATIO':1.6,'SPACING_COMPONENT_COMPONENT':c['spacing'],'COMPACTION_CONNECTED_COMPONENTS':True,'EDGE_ROUTING':'ORTHOGONAL','DIRECTION':'RIGHT'});nodes={};ports={}
        for item in inputs['nodes']:
            n=LNode(g,properties=CanonicalPropertyMap());n.labels=[];n.pos=Vec2(*map(float,item['pos']));n.size=Vec2(*map(float,item['size']));n.margin=Insets(*map(float,item['margin']));n.type=item['type']
            if item['side']:n.properties['EXT_PORT_SIDE']=item['side']
            g.layerless_nodes.append(n);nodes[item['id']]=n;original_nodes.append(n);refs.append((n.pos,n.size))
        for item in inputs['ports']:
            p=LPort(properties=CanonicalPropertyMap());p.labels=[];set_port_owner(p,nodes[item['owner']]);p.size=Vec2(*map(float,item['size']));set_side(p,item['side']);p.pos=Vec2(*map(float,item['pos']));p.anchor=Vec2(*map(float,item['anchor']));ports[item['id']]=p
        for item in inputs['edges']:
            e=LEdge(properties=CanonicalPropertyMap());e.labels=[];set_source(e,ports[item['source']]);set_target(e,ports[item['target']]);e.bend_points.extend(Vec2(*map(float,v))for v in item['bends']);label=LLabel(item['id']);label.pos=Vec2(*map(float,item['labelPos']));e.labels.append(label);e.properties['EDGE_THICKNESS']=item['thickness'];original_edges.append(e)
        graphs.append(g)
    target=LGraph(None,None,None);target.properties=CanonicalPropertyMap();compactor=None;prepared=[];old_transform=cc.ComponentsCompactor.transform_graph;old_compact=cc.ComponentsCompactor.compact
    def observe_compact(owner,*a,**kw):
        global compactor
        compactor=owner;return old_compact(owner,*a,**kw)
    cc.ComponentsCompactor.compact=observe_compact
    def transform(self,g):
        result=old_transform(self,g);prepared.append({'regularFlag':result.contains_regular_nodes,'regularFlagType':'boolean'if type(result.contains_regular_nodes)is bool else'number','hull':[box(r)for r in result.rectilinear_convex_hull],
            'extensions':[{'side':e.side,'rectangle':box(e.extension),'placeholder':box(e.placeholder),'edgeCount':len(e.edges.values())}for e in result.external_extensions]});return result
    cc.ComponentsCompactor.transform_graph=transform
    failure=None
    try:
        placer={'group':ComponentGroupGraphPlacer,'model-order-group':ComponentGroupModelOrderGraphPlacer,'model-order-row':ModelOrderRowGraphPlacer}[c['placer']]();placer.combine(graphs,target)
    except ReferenceError as error:failure={'name':type(error).__name__,'message':str(error)}
    finally:cc.ComponentsCompactor.transform_graph=old_transform;cc.ComponentsCompactor.compact=old_compact
    all_nodes=[n for g in graphs for n in g.layerless_nodes];edges=[]
    for n in all_nodes:
        for p in n.ports:
            for e in p.outgoing_edges:
                if not any(e is v for v in edges):edges.append(e)
    edge=original_edges[0];fake=LEdge(properties=CanonicalPropertyMap());fake.labels=[LLabel('invalid-control')];set_source(fake,edge.source);set_target(fake,edge.target);invalid=None
    if edge.source.owner.type=='NORMAL' and edge.target.owner.type=='NORMAL':
        try:cc.InternalExternalExtension(fake)
        except ValueError as error:invalid=str(error)
    set_source(fake,None);set_target(fake,None)
    actual.append({'targetSize':point(target.size),'targetNodes':[{'pos':point(n.pos),'owner':n.graph is target}for n in target.layerless_nodes],'name':c['name'],'failed':failure is not None,'error':failure,'prepared':prepared,'graphTopLeft':point(compactor.graph_top_left),'graphBottomRight':point(compactor.graph_bottom_right),'size':None if failure else point(compactor.compacted_graph_size),'offset':None if failure else point(compactor.yet_another_offset),
        'sizeReferenceSame':None if failure else compactor.compacted_graph_size is compactor.compactor.transformer.graph_size,
        'graphs':[{'size':point(g.size),'offset':point(g.offset),'nodes':[{'type':n.type,'pos':point(n.pos),'size':point(n.size),'ports':[{'pos':point(p.pos),'anchor':point(p.anchor),'side':p.side}for p in n.ports]}for n in g.layerless_nodes]}for g in graphs],
        'edges':[{'sourceNode':all_nodes.index(e.source.owner),'targetNode':all_nodes.index(e.target.owner),'bends':[point(v)for v in e.bend_points],'labels':[point(l.pos)for l in e.labels],
            'hasJunction':_has_property(e,'JUNCTION_POINTS'),'junctions':[point(v)for v in _read_property(e,'JUNCTION_POINTS')]if _has_property(e,'JUNCTION_POINTS')else None}for e in edges],
        'originalNodeReferences':[n.pos is refs[i][0] and n.size is refs[i][1]for i,n in enumerate(original_nodes)],'invalidError':invalid})
comparison=diff([original['value'][i]for i in selected],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
    'actualConnectedCompactor':True,'actualPlacerConsumer':True,'inputGeometryExplicitlySupplied':True,'selectedCaseIndexes':selected,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
