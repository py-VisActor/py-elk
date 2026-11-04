from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.self_loops_general import SelfLoopHolder,needs_self_loop_processing
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['DIRECTION']='RIGHT';g.properties['SPACING_LABEL_LABEL']=2;n=LNode(g);other=LNode(g);g.layerless_nodes=[n,other];ports=[]
for i in range(6):
    p=LPort(n if i!=5 else other,id=20+i);p.labels=[];p.side='EAST'if i%2 else'WEST';p.owner.ports.append(p);ports.append(p)
def edge(number,a,b,w=None,h=None):
    e=LEdge(id=number);e.labels=[];set_source(e,ports[a]);set_target(e,ports[b])
    if w is not None:e.labels.append(SimpleNamespace(id=number,pos=Vec2(),size=Vec2(w,h),properties=CanonicalPropertyMap()))
    return e
e0=edge(10,0,1,8,4);e1=edge(11,1,2,10,3);e2=edge(12,3,4,6,5);non=edge(13,0,5);holder=SelfLoopHolder(n);holder.initialize();names={p:i for i,p in enumerate(ports)};loops=[]
vec=lambda v:[v.x,v.y]
for loop in holder.sl_hyper_loops:
    labels=loop.sl_labels;labels.position=Vec2(5,6);labels.alignment='CENTER';labels.side='NORTH';labels.apply_placement(Vec2(2,3))
    loops.append({'ports':[names[p.l_port]for p in loop.sl_ports],'edges':[e.l_edge.id for e in loop.sl_edges.values()],'edgeLoopSame':all(e.sl_hyper_loop is loop for e in loop.sl_edges.values()),'labels':{'ids':[l.id for l in labels.l_labels],'size':vec(labels.size),'positions':[vec(l.pos)for l in labels.l_labels]}})
actual={'holder':{'ports':[{'port':names[p.l_port],'id':p.l_port.id,'incoming':[e.l_edge.id for e in p.incoming_sl_edges],'outgoing':[e.l_edge.id for e in p.outgoing_sl_edges],'hadOnlySelfLoops':p.had_only_self_loops,'isHidden':p.is_hidden}for _,p in holder.sl_ports.items()],'loops':loops,'routingSlots':holder.routing_slot_count,'portsHidden':holder.are_ports_hidden,'nodeSame':holder.l_node is n},'nonSelfUnchanged':non.source is ports[0]and non.target is ports[5],'nodePortOrder':[names[p]for p in n.ports],'needs':[needs_self_loop_processing(n),needs_self_loop_processing(other)]}
raw=json.loads(original.read_text(encoding='utf8'));comparison=diff(raw['value'],actual);assert before==hashes();out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'One new actual foundation object group only. Shared-port two-edge hyperloop and disjoint loop; retained nonself edge; linked holder order, BFS IDs, hadOnly values, actual label accumulation/placement. No four processors, routing, holder mutation replay or whole layout claim.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
