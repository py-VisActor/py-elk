from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.self_loops_general import SelfLoopHolder,self_loop_postprocessor
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.execution.diagnostics import BasicProgressMonitor
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['DIRECTION']='RIGHT';layer=Layer(g);g.layers.append(layer);n=LNode(g);other=LNode(g);set_layer(n,layer);set_layer(other,layer);n.properties=CanonicalPropertyMap();n.pos=Vec2(11,17);p=LPort(n);q=LPort(n);t=LPort(other);n.ports=[p,q];other.ports=[t];p.side=q.side='NORTH'
e=LEdge(id=7);e.labels=[];set_source(e,p);set_target(e,q);e.bend_points=[Vec2(-8,-4),Vec2(30,-4)];label=SimpleNamespace(pos=Vec2(999,888),size=Vec2(12,5),id=0,properties=CanonicalPropertyMap());e.labels.append(label)
other_edge=LEdge(id=8);other_edge.labels=[];set_source(other_edge,p);set_target(other_edge,t);holder=SelfLoopHolder(n);holder.initialize();n.properties['SELF_LOOP_HOLDER']=holder;loop=holder.sl_hyper_loops[0];loop.sl_labels.position=Vec2(2,-9);loop.sl_labels.alignment='LEFT';loop.sl_labels.side='NORTH'
prior=[x.id for x in p.outgoing_edges];monitor=BasicProgressMonitor(False,False);self_loop_postprocessor(g,monitor=monitor);vec=lambda v:[v.x,v.y]
actual={'before':prior,'outgoing':[x.id for x in p.outgoing_edges],'incoming':[x.id for x in q.incoming_edges],'sameEndpoints':e.source is p and e.target is q,'bends':[vec(x)for x in e.bend_points],'label':vec(label.pos),'holderSame':n.properties['SELF_LOOP_HOLDER']is holder,'portsHidden':holder.are_ports_hidden,'loopCount':len(holder.sl_hyper_loops),'nodePosition':vec(n.pos),'monitorRunning':monitor.is_running(),'otherUnchanged':other_edge.source is p and other_edge.target is t}
raw=json.loads(original.read_text(encoding='utf8'));comparison=diff(raw['value'],actual);assert hashes()==before;out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'One new routed DTO runs actual full SelfLoopPostProcessor; same endpoints move original edge behind nonself outgoing, bends shift then labels apply offset, holder retained. Other loop phases/geometry routers and complete layout not claimed.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
