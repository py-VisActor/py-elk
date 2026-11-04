"""PRIVATE_SRC REQUEST ORIGINAL REPORT; actual produced chains and switcher."""
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
from pyelk.algorithms.layered.long_edges_general import long_edge_splitter
from pyelk.algorithms.layered.center_label_switcher import LabelDummySwitcher,LabelDummyInfo
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads(request_path.read_bytes());o=json.loads(original_path.read_bytes())
assert o['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert o['requestSha256']==sha(request_path)and o['probeSha256']==sha(Path(__file__).with_name('label-switcher-context-probe.cjs'))
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')};sw=LabelDummySwitcher();actual=[]
class Quiet:
    def begin(self,*args):pass
    def done(self):pass
for c in r['cases']:
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap({'DIRECTION':c.get('direction','RIGHT'),'SPACING_EDGE_LABEL':2,'SPACING_LABEL_LABEL':1,'SPACING_EDGE_NODE_BETWEEN_LAYERS':4.25,'SPACING_NODE_NODE_BETWEEN_LAYERS':7.75,'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY':c['strategy']})
    a=LNode(g,properties=CanonicalPropertyMap());b=LNode(g,properties=CanonicalPropertyMap());a.size.x=10.0;b.size.x=10.0;g.layerless_nodes.extend([a,b])
    p=LPort(properties=CanonicalPropertyMap());q=LPort(properties=CanonicalPropertyMap());set_port_owner(p,a);set_port_owner(q,b);set_side(p,'EAST');set_side(q,'WEST')
    e=LEdge(properties=CanonicalPropertyMap({'EDGE_THICKNESS':3,'REVERSED':c.get('reversed',False)}));set_source(e,p);set_target(e,q);labels=[];events=[]
    for width in(12,7):
        l=LLabel(None);l.size=Vec2(float(width),2.0);l.properties=CanonicalPropertyMap({'EDGE_LABELS_PLACEMENT':'CENTER'});e.labels.append(l);labels.append(l)
    if c.get('nullOverride'):
        labels[0].properties._values[canonical_property_key('EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY')]=None
        labels[1].properties['EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY']='TAIL_LAYER'
    label_dummy_inserter(g,monitor=Quiet());dummy=next(n for n in g.layerless_nodes if n is not a and n is not b)
    layers=[Layer(g)for _ in range(5)];g.layers.extend(layers);g.layerless_nodes.clear();set_layer(a,layers[0]);set_layer(dummy,layers[1]);set_layer(b,layers[4]);extra=LNode(g,properties=CanonicalPropertyMap());extra.size.x=0.0 if c.get('zeroWidths')else 20.0;set_layer(extra,layers[3]);long_edge_splitter(g,monitor=Quiet())
    longs=[next(n for n in layers[i].nodes if n.type=='LONG_EDGE')for i in(2,3)];nodes=[a,dummy,*longs,extra,b];names=['source','label','long2','long3','extra','target'];name=lambda n:names[next(i for i,item in enumerate(nodes)if item is n)]
    for i,layer in enumerate(layers):layer.id=i;layer.size.x=0.0 if c.get('zeroWidths')else 20.0 if i==3 else 10.0 if i in(0,4)else 0.0
    info=LabelDummyInfo(dummy,c['strategy']);info_before={'strategy':info.placement_strategy,'left':[name(n)for n in info.left_long_edge_dummies],'right':[name(n)for n in info.right_long_edge_dummies],'range':[info.leftmost_layer_id,info.rightmost_layer_id]}
    class Monitor:
        def begin(self,task,work):events.append(['begin',task,work])
        def done(self):events.append(['done'])
    sw.process(g,Monitor());edges=[]
    for n in nodes:
        for port in n.ports:
            for edge in port.outgoing_edges:
                if not any(edge is item for item in edges):edges.append(edge)
    actual.append({'name':c['name'],'events':events,'beforeInfo':info_before,'layers':[[name(n)for n in layer.nodes]for layer in layers],'labelLayer':dummy.layer.id,'alignment':dummy.properties.get('ALIGNMENT','AUTOMATIC'),'markers':[{'node':name(n),'has':_has_property(n,'LONG_EDGE_BEFORE_LABEL_DUMMY'),'value':n.properties.get('LONG_EDGE_BEFORE_LABEL_DUMMY',False)}for n in longs],'includes':[l.properties.get('edgelabelcenterednessanalysis.includelabel',False)for l in labels],'edges':[[name(edge.source.owner),name(edge.target.owner)]for edge in edges],'fieldReset':sw.layer_widths is None,'firstOverrideHas':_has_property(labels[0],'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY')})
comparison=diff(o['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'requestSha256':sha(request_path),'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'explicitLayerGeometry':True,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
