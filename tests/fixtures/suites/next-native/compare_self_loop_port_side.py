from pathlib import Path
import sys,json,hashlib
source,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.self_loops_general import self_loop_preprocessor,assign_port_sides
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();results=[]
for strategy in('EQUALLY','NORTH','NORTH_SOUTH'):
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();n=LNode(g);n.properties=CanonicalPropertyMap();other=LNode(g);other.properties=CanonicalPropertyMap();g.layerless_nodes=[n,other];names={};all_ports=[]
    n.properties['PORT_CONSTRAINTS']='FREE';n.properties['EDGE_ROUTING_SELF_LOOP_DISTRIBUTION']=strategy;eid=0
    for i in range(8):
        count=[3,2,5,2,4,3,4,2][i];ports=[]
        for j in range(count):
            p=LPort(n);p.labels=[];p.properties=CanonicalPropertyMap();n.ports.append(p);p.side='WEST';p.size=Vec2(4+j,6+j)
            if j==count-1:p.explicitly_supplied_port_anchor=True;p.anchor=Vec2(9,8)
            names[p]=str(i)+'.'+str(j);ports.append(p);all_ports.append(p)
        for j in range(count-1):
            e=LEdge(id=eid);eid+=1;e.labels=[];set_source(e,ports[j]);set_target(e,ports[j+1])
        if i%2==0:
            target=LPort(other);target.labels=[];other.ports.append(target);e=LEdge(id=eid);eid+=1;e.labels=[];set_source(e,ports[0]);set_target(e,target)
    self_loop_preprocessor(g);holder=n.properties['SELF_LOOP_HOLDER'];prior=[[names[p.l_port]for p in loop.sl_ports]for loop in holder.sl_hyper_loops];assign_port_sides(holder)
    results.append({'strategy':strategy,'before':prior,'after':[[names[p.l_port]for p in loop.sl_ports]for loop in holder.sl_hyper_loops],
                    'ports':[{'name':names[p],'side':p.side,'anchor':[p.anchor.x,p.anchor.y],'ownerPresent':p.owner is not None}for p in all_ports],
                    'visible':[names[p]for p in n.ports],'hidden':[{'name':names[p],'hidden':slp.is_hidden}for p,slp in holder.sl_ports.items()]})
raw=json.loads(original.read_text(encoding='utf8'));comparison=diff(raw['value'],results);assert before==hashes();out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':results,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'One new group3 distributions each25 actual ports/8loops; actual native preprocessor creates holders/disconnects edges/hides only all-selfloop ports, then actual distribution assignment/source sorting/explicit anchor behavior. No port restorer/router or complete layout claim.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
