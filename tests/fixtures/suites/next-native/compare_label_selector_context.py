"""PRIVATE_SRC REQUEST ORIGINAL REPORT; actual six-mode selector contexts."""
import hashlib,json,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_port_owner,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_import import LLabel
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap,canonical_property_key
from pyelk.algorithms.layered.native_adapters import _has_property
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.center_label_dummies import label_dummy_inserter
from pyelk.algorithms.layered.label_side_selector import label_side_selector,gather_labels
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
o=json.loads(original_path.read_bytes());r=json.loads(request_path.read_bytes())
assert o['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert o['requestSha256']==sha(request_path)and o['probeSha256']==sha(Path(__file__).with_name('label-selector-context-probe.cjs'))
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')};actual=[]
for mode in r['modes']:
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'DIRECTION':'RIGHT','SPACING_EDGE_LABEL':2,'SPACING_LABEL_LABEL':1,'EDGE_LABELS_SIDE_SELECTION':mode})
    a=LNode(g,properties=CanonicalPropertyMap());b=LNode(g,properties=CanonicalPropertyMap());g.layerless_nodes.extend([a,b]);ports=[];labels=[];names=[];events=[]
    for side in('EAST','EAST','NORTH'):
        p=LPort(properties=CanonicalPropertyMap());set_port_owner(p,a);set_side(p,side);ports.append(p)
    q=LPort(properties=CanonicalPropertyMap());set_port_owner(q,b);set_side(q,'WEST')
    def edge(source_port,target_port,reversed):
        e=LEdge(properties=CanonicalPropertyMap({'EDGE_THICKNESS':3,'REVERSED':reversed}));set_source(e,source_port);set_target(e,target_port);return e
    def label(e,name,placement,inline):
        l=LLabel(None);l.size=Vec2(4.0,2.0);l.properties=CanonicalPropertyMap({'EDGE_LABELS_PLACEMENT':placement,'EDGE_LABELS_INLINE':inline});e.labels.append(l);labels.append(l);names.append(name);return l
    e0=edge(ports[0],q,True);e1=edge(ports[1],q,False);loop=edge(ports[2],ports[2],False)
    label(e0,'c0','CENTER',False);h0=label(e0,'h0','HEAD',False);label(e1,'c1','CENTER',True);t1=label(e1,'t1','TAIL',False);label(e1,'h1','HEAD',False);lt=label(loop,'loop-tail','TAIL',False);label(loop,'loop-head','HEAD',False)
    h0.properties._values[canonical_property_key('END_LABEL_EDGE')]=None
    class Quiet:
        def begin(self,*args):pass
        def done(self):pass
    label_dummy_inserter(g,monitor=Quiet());dummies=[n for n in g.layerless_nodes if n is not a and n is not b]
    layers=[Layer(g),Layer(g),Layer(g)];g.layers.extend(layers);g.layerless_nodes.clear();set_layer(a,layers[0])
    for n in dummies:set_layer(n,layers[1])
    set_layer(b,layers[2]);dummy_before=[{'size':[n.size.x,n.size.y],'portYs':[p.pos.y for p in n.ports]}for n in dummies]
    class Monitor:
        def begin(self,name,work):events.append(['begin',name,work])
        def done(self):events.append(['done'])
    label_side_selector(g,monitor=Monitor());empty=gather_labels(ports[0]);tails=gather_labels(ports[1]);loop_labels=gather_labels(ports[2])
    bag=lambda values:[names[next(i for i,item in enumerate(labels)if item is l)]for l in values]
    actual.append({'mode':mode,'events':events,'dummyBefore':dummy_before,'dummies':[{'side':n.properties.get('LABEL_SIDE','UNKNOWN'),'height':n.size.y,'portYs':[p.pos.y for p in n.ports]}for n in dummies],'labelSides':[{'name':name,'side':l.properties.get('LABEL_SIDE','UNKNOWN')}for name,l in zip(names,labels)],'emptyBagNonnull':empty is not None,'emptyBagLength':None if empty is None else len(empty),'tailBag':bag(tails),'loopBag':bag(loop_labels),'sameLoopTailTwice':len(loop_labels)==2 and loop_labels[0]is lt and loop_labels[1]is lt,'h0MarkerPresent':_has_property(h0,'END_LABEL_EDGE'),'h0MarkerNullish':h0.properties.get('END_LABEL_EDGE')is None,'t1MarkerOriginal':t1.properties.get('END_LABEL_EDGE')is e1,'portMaximums':[p.properties.get('MAX_EDGE_THICKNESS',0)for p in ports]})
comparison=diff(o['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'requestSha256':sha(request_path),'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'explicitLayerSetup':True,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
