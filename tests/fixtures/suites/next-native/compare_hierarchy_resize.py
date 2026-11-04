"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: new hierarchy resize objects only."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5])
sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,Layer,Vec2,Insets,set_layer,set_port_owner
from pyelk.algorithms.layered.native_import import LLabel
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.native_adapters import _read_property,_has_property
from pyelk.algorithms.layered.hierarchical_resize import hierarchical_node_resizing_processor
from pyelk.algorithms.layered.ports import set_side
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.global_properties import parse_global_mapping
from pyelk.execution.node_micro import _native
from pyelk.execution.diagnostics import BasicProgressMonitor
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
original=json.loads(original_path.read_bytes());request=json.loads(request_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path)
assert original['probeSha256']==sha(Path(__file__).with_name('hierarchy-resize-probe.cjs'))
assert original['actualHierarchicalResize'] is True and original['layoutExecuted'] is False
metadata=NativeMetadataService(['layered'])
def graph():
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();return g
def node(g):
    n=LNode(g);n.properties=CanonicalPropertyMap();n.labels=[];return n
def number(v):
    return 'NaN' if math.isnan(v) else ('Infinity' if v>0 else '-Infinity') if not math.isfinite(v) else '-0' if v==0 and math.copysign(1,v)<0 else v
def point(v):return [number(v.x),number(v.y)]
actual=[]
for c in request['cases']:
    outer=graph();parent=node(outer);g=graph();outer.layerless_nodes.append(parent)
    outer.properties['GRAPH_PROPERTIES']=set();parent.size=Vec2(*c['parentSize'])
    if c['parent']:g.parent_node=parent
    g.size=Vec2(*c['size']);g.offset=Vec2(3.0,4.0);g.padding=Insets(1.0,2.0,3.0,4.0)
    g.properties.update({k:_native(v) for k,v in parse_global_mapping(c['options'],metadata=metadata).items()})
    g.properties['GRAPH_PROPERTIES']={'EXTERNAL_PORTS'} if c['external'] else set()
    ports=[];nodes=[];layers=[]
    for i,side in enumerate(('NORTH','EAST','SOUTH','WEST')):
        p=LPort();p.properties=CanonicalPropertyMap();set_port_owner(p,parent)
        p.size=Vec2(2.0,4.0);p.pos=Vec2(2.0+i,3.0+i);p.anchor=Vec2(9.0,11.0);set_side(p,side);ports.append(p)
        n=node(g);n.id=i;n.type='EXTERNAL_PORT';n.pos=Vec2(7.0+i,9.0+i);n.size=Vec2(4.0,6.0)
        n.properties.update({'EXT_PORT_SIDE':side,'PORT_BORDER_OFFSET':2.5,'ORIGIN':p});nodes.append(n)
        if i<2:g.layerless_nodes.append(n)
        else:
            l=Layer(g);g.layers.append(l);layers.append(l);set_layer(n,l,0)
    ignored=node(g);ignored.id=4;ignored.properties['ORIGIN']={'pos':{'x':999,'y':999}};g.layerless_nodes.append(ignored);nodes.append(ignored)
    for x,y,w,h in ((9,1,2,2),(1,19,2,2),(1,1,2,2),(9,19,2,2),(-8,30,2,2),(30,-8,2,2)):
        l=LLabel();l.pos=Vec2(float(x),float(y));l.size=Vec2(float(w),float(h));parent.labels.append(l)
    refs=[g.layers,g.layerless_nodes,g.size,g.offset,parent.size,*[p.pos for p in ports],*[l.pos for l in parent.labels]]
    monitor=BasicProgressMonitor();hierarchical_node_resizing_processor(g,monitor=monitor)
    minimum=_read_property(g,'NODE_SIZE_MINIMUM') if _has_property(g,'NODE_SIZE_MINIMUM') else None
    after_refs=[g.layers,g.layerless_nodes,g.size,g.offset,parent.size,*[p.pos for p in ports],*[l.pos for l in parent.labels]]
    actual.append({'name':c['name'],'size':point(g.size),'offset':point(g.offset),'minimum':point(minimum)if minimum is not None else None,
      'nodes':[{'id':n.id,'pos':point(n.pos),'layerNull':n.layer is None}for n in g.layerless_nodes],'layers':len(g.layers),'oldLayerCounts':[len(l.nodes)for l in layers],
      'parentSize':point(parent.size),'portConstraints':_read_property(parent,'PORT_CONSTRAINTS'),'parentConstraints':sorted(_read_property(parent,'NODE_SIZE_CONSTRAINTS')),'outerProperties':sorted(_read_property(outer,'GRAPH_PROPERTIES')),
      'ports':[{'pos':point(p.pos),'anchor':point(p.anchor),'side':p.side}for p in ports],'labels':[point(l.pos)for l in parent.labels],'monitorFinished':not monitor.is_running(),
      'references':[a is b for a,b in zip(refs,after_refs)]})
comparison=diff(original['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
        'actualHierarchicalResize':True,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
