from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.native_adapters import LPortAdapter,innermost_node_margin_processor
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_layer,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.execution.diagnostics import BasicProgressMonitor
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();layer=Layer(g);g.layers.append(layer);n=LNode(g);n.properties=CanonicalPropertyMap();n.labels=[];set_layer(n,layer);n.pos=Vec2(11,12);n.size=Vec2(30,20)
p=LPort(n);p.labels=[];p.properties=CanonicalPropertyMap();n.ports.append(p);p.side='WEST';p.pos=Vec2(-3,8);p.size=Vec2(3,4)
e=LEdge(id=7);e.labels=[];set_source(e,p);set_target(e,p)
slp=SimpleNamespace(incoming_sl_edges=[],outgoing_sl_edges=[]);slh=SimpleNamespace(sl_ports={p:slp});sle=SimpleNamespace(l_edge=e);slp.incoming_sl_edges.append(sle);slp.outgoing_sl_edges.append(sle);n.properties['SELF_LOOP_HOLDER']=slh
dummy=LNode(g);dp=LPort(dummy);dummy.ports.append(dp);de=LEdge(id=9);dp.incoming_edges.append(de);dp.outgoing_edges.append(de);p.properties['PORT_DUMMY']=dummy
edges=lambda values:[x.element.id for x in values]
v=LPortAdapter(p,True);incoming=v.incoming_edges;outgoing=v.outgoing_edges;raw=LPortAdapter(p,False);initial={'incoming':edges(incoming),'outgoing':edges(outgoing),'nontransparent':edges(raw.incoming_edges)}
later=SimpleNamespace(l_edge=LEdge(id=10));slp.incoming_sl_edges.append(later);slp.outgoing_sl_edges.append(later);initial['cached']=edges(v.incoming_edges);initial['same']=incoming is v.incoming_edges
missing=LPort(n);missing.properties=CanonicalPropertyMap();n.ports.append(missing);initial['missingPort']=edges(LPortAdapter(missing,True).incoming_edges)
def label(x,y,w,h):return SimpleNamespace(pos=Vec2(x,y),size=Vec2(w,h),properties=CanonicalPropertyMap(),id=0)
l=label(-9,-5,8,4);n.labels.append(l);pl=label(-6,0,5,7);p.labels.append(pl);el=label(0,0,80,40);el.properties['EDGE_LABELS_PLACEMENT']='HEAD';e.labels.append(el)
monitor=BasicProgressMonitor(False,False);innermost_node_margin_processor(g,monitor=monitor)
actual={'sl':initial,'innermost':{'margin':[n.margin.top,n.margin.right,n.margin.bottom,n.margin.left],'position':[n.pos.x,n.pos.y],'size':[n.size.x,n.size.y],'label':[l.pos.x,l.pos.y],'portLabel':[pl.pos.x,pl.pos.y],'monitorRunning':monitor.is_running(),'physicalEdgeLabelSize':[el.size.x,el.size.y]}}
original_value=json.loads(original.read_text(encoding='utf8'));comparison=diff(original_value['value'],actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':original_value['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'New actual source SelfLoopHolder/Port/Edge DTO to native canonical ABI: own,dummy,selfloop encounter order and caching; actual Innermost wrapper excludes head/tail labels, preserves geometry, finishes monitor. Not complete loop preprocessing/math or whole layout.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
