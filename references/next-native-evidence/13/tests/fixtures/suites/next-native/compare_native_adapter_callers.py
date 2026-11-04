from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.native_adapters import (LPortAdapter,LGraphAdapter,_compare_ports,NodeMarginCalculator,label_and_node_size_processor,place_external_port_dummy_labels)
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,Insets,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes()
def label(x,y,w,h):return SimpleNamespace(pos=Vec2(x,y),size=Vec2(w,h),properties=CanonicalPropertyMap(),id=0)
def graph():
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();l=Layer(g);g.layers.append(l);return g,l
def node(g,l=None):
    n=LNode(g);n.labels=[];n.properties=CanonicalPropertyMap()
    if l is not None:set_layer(n,l)
    return n
def port(n):
    p=LPort(n);p.labels=[];p.properties=CanonicalPropertyMap();n.ports.append(p);return p
def edge(number):
    e=LEdge(id=number);e.labels=[];return e
vec=lambda v:[v.x,v.y];ins=lambda v:[v.top,v.right,v.bottom,v.left]
g,l=graph();n=node(g,l);n.pos=Vec2(10,20);n.size=Vec2(40,30);p=port(n);p.side='EAST';p.pos=Vec2(40,8);p.size=Vec2(4,3)
own=edge(1);p.incoming_edges.append(own);p.outgoing_edges.append(own)
dummy=node(g);dp=port(dummy);extra=edge(2);dp.incoming_edges.extend([own,extra]);dp.outgoing_edges.append(extra);p.properties['PORT_DUMMY']=dummy
pv=LPortAdapter(p,True);incoming=pv.incoming_edges;outgoing=pv.outgoing_edges;p.incoming_edges.append(extra)
ns=node(g);ns.type='NORTH_SOUTH_PORT';nsp=port(ns);nsp.incoming_edges.append(own);nsp.properties['PORT_DUMMY']=dummy;nsv=LPortAdapter(nsp,True)
p2=port(n);p2.side='EAST';p2.pos.y=-2;p.properties['PORT_INDEX']=0;p2.properties['PORT_INDEX']=2;indexed=_compare_ports(p,p2);del p2.properties['PORT_INDEX'];geometric=_compare_ports(p,p2)
port_result={'incoming':[e.element.id for e in incoming],'outgoing':[e.element.id for e in outgoing],'sameCache':incoming is pv.incoming_edges,'nsEmpty':len(nsv.incoming_edges)==0,'nsSameEmpty':nsv.incoming_edges is nsv.outgoing_edges,'indexed':indexed,'geometric':geometric,'anchorNull':pv.get_property('PORT_ANCHOR')is None,'anchorHas':pv.has_property('PORT_ANCHOR')}
n.labels.append(label(-7,-8,20,6));p.labels.append(label(2,-4,13,7));tail=label(999,999,20,9);head=label(999,999,12,8);tail.properties['EDGE_LABELS_PLACEMENT']='TAIL';head.properties['EDGE_LABELS_PLACEMENT']='HEAD';own.labels.extend([tail,head])
ga=LGraphAdapter(g,False,False);calc=NodeMarginCalculator(ga);calc.process();full=ins(n.margin);calc.exclude_edge_head_tail_labels().process();without=ins(n.margin)
sg,sl=graph();sn=node(sg,sl);sn.size=Vec2(30,20);sp=port(sn);sp.side='EAST';sp.size=Vec2(2,3);sp.labels.append(label(0,0,12,6));sn.labels.append(label(0,0,18,7))
label_and_node_size_processor(sg)
sized={'size':vec(sn.size),'padding':ins(sn.padding),'port':vec(sp.pos),'portLabel':vec(sp.labels[0].pos),'nodeLabel':vec(sn.labels[0].pos),'portId':sp.id}
ext=node(sg);ep=port(ext);ext.size=Vec2(20,40);ep.pos=Vec2(5,7);ep.connected_to_external_nodes=False;ep.labels.extend([label(0,0,8,3),label(0,0,6,4)]);ext.properties['EXT_PORT_SIDE']='EAST'
place_external_port_dummy_labels(ext,{'OUTSIDE'},True,True);outside=[vec(x.pos)for x in ep.labels];ext.properties['EXT_PORT_SIDE']='NORTH';place_external_port_dummy_labels(ext,{'INSIDE'},True,False)
actual={'ports':port_result,'margin':{'full':full,'withoutEdges':without},'sized':sized,'external':{'outside':outside,'inside':[vec(x.pos)for x in ep.labels]}}
raw=json.loads(original.read_text(encoding='utf8'));comparison=diff(raw['value'],actual);after=hashes();assert before==after
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'New Port own/dummy duplicate order, cache/NS EMPTY, nullable anchor, boxed-index comparator; actual margin with/without headtail; normal size wrapper; external label two branches. No selfloop-holder execution or complete pipeline certification.'}
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
