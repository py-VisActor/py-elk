"""PRIVATE_SRC REQUEST ORIGINAL REPORT; actual insert / supplied state / remove."""
import hashlib,json,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_port_owner,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_import import LLabel
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.native_adapters import _read_property,_has_property
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.center_label_dummies import label_dummy_inserter,label_dummy_remover
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(request_path.read_bytes());o=json.loads(original_path.read_bytes())
assert o['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert o['requestSha256']==sha(request_path)and o['probeSha256']==sha(Path(__file__).with_name('center-label-lifecycle-probe.cjs'))
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')};actual=[]
point=lambda v:[v.x,v.y]
for direction in r['directions']:
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'DIRECTION':direction,'SPACING_EDGE_LABEL':r['edgeLabelSpacing'],'SPACING_LABEL_LABEL':r['labelSpacing'],'EDGE_ROUTING':'ORTHOGONAL'})
    a=LNode(g,properties=CanonicalPropertyMap());b=LNode(g,properties=CanonicalPropertyMap());g.layerless_nodes.extend([a,b])
    p=LPort(properties=CanonicalPropertyMap());q=LPort(properties=CanonicalPropertyMap());set_port_owner(p,a);set_port_owner(q,b);set_side(p,'EAST');set_side(q,'WEST')
    e=LEdge(properties=CanonicalPropertyMap({'EDGE_THICKNESS':r['thickness']}));set_source(e,p);set_target(e,q);labels=[];events=[]
    for item in r['labels']:
        label=LLabel(None);label.size=Vec2(*map(float,item['size']));label.pos=Vec2(1.0,2.0);label.properties=CanonicalPropertyMap({'EDGE_LABELS_INLINE':item['inline']})
        if 'placement'in item:label.properties['EDGE_LABELS_PLACEMENT']=item['placement']
        e.labels.append(label);labels.append(label)
    names=lambda values:[r['labels'][next(i for i,item in enumerate(labels)if item is label)]['name']for label in values]
    class Monitor:
        def begin(self,name,work):events.append(['begin',name,work])
        def done(self):events.append(['done'])
    monitor=Monitor();label_dummy_inserter(g,monitor=monitor)
    dummy=next(n for n in g.layerless_nodes if n is not a and n is not b);represented=dummy.properties['REPRESENTED_LABELS'];represented_ref=represented;original_labels=e.labels
    segment=next(port for port in dummy.ports if port.side=='EAST').outgoing_edges[0]
    inserted={'dummySize':point(dummy.size),'portYs':[port.pos.y for port in dummy.ports],'represented':names(represented),'surviving':names(e.labels),'segment':names(segment.labels),'thickness':e.properties['EDGE_THICKNESS']}
    layers=[Layer(g),Layer(g),Layer(g)];g.layers.extend(layers);g.layerless_nodes.clear();set_layer(a,layers[0]);set_layer(dummy,layers[1]);set_layer(b,layers[2]);dummy.pos=Vec2(*map(float,r['dummyPosition']));dummy.properties['LABEL_SIDE']='BELOW'
    label_dummy_remover(g,monitor=monitor)
    actual.append({'direction':direction,'events':events,'inserted':inserted,'finalLabels':names(e.labels),'positions':[point(l.pos)for l in labels],'sameOriginalLabels':e.labels is original_labels,'sameRepresented':dummy.properties['REPRESENTED_LABELS']is represented_ref,'dummyLayerRetained':dummy.layer is layers[1],'middleLayerEmpty':not layers[1].nodes,'survivorTargetRestored':e.target is q,'segmentDetached':segment.source is None and segment.target is None,'junctionPresence':[_has_property(e,'JUNCTION_POINTS'),_has_property(segment,'JUNCTION_POINTS')],'junctionsDistinct':_read_property(e,'JUNCTION_POINTS')is not _read_property(segment,'JUNCTION_POINTS')})
comparison=diff(o['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'requestSha256':sha(request_path),'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'explicitIntermediateGeometry':True,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
