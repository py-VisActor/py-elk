from pathlib import Path
import sys,json,hashlib
source,request,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.self_loops_general import self_loop_preprocessor,self_loop_port_restorer,RoutingDirector,_SIDES
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.native_adapters import _compare_ports
from pyelk.algorithms.layered.ports import _source_sort,set_side
from pyelk.execution.diagnostics import BasicProgressMonitor
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();results=[]
def make_port(node,name,names):
    p=LPort(node);p.labels=[];p.properties=CanonicalPropertyMap();node.ports.append(p);names[p]=name;return p
def edge(source,target,eid):
    e=LEdge(id=eid);e.labels=[];set_source(e,source);set_target(e,target);return e
for inputs in json.loads(request.read_text(encoding='utf8'))['cases']:
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['DIRECTION']='RIGHT';n=LNode(g);other=LNode(g);n.properties=CanonicalPropertyMap();other.properties=CanonicalPropertyMap();g.layerless_nodes=[n,other];names={};all_ports=[]
    n.properties['PORT_CONSTRAINTS']=inputs['constraints'];n.properties['ORIGINAL_PORT_CONSTRAINTS']=inputs['constraints'];n.properties['EDGE_ROUTING_SELF_LOOP_DISTRIBUTION']=inputs['distribution'];n.properties['EDGE_ROUTING_SELF_LOOP_ORDERING']=inputs['ordering'];eid=0
    for i,sequence in enumerate(inputs['loops']):
        ports=[]
        for j,side in enumerate(sequence):
            p=make_port(n,'loop'+str(i)+'.'+str(j),names);set_side(p,side);ports.append(p);all_ports.append(p)
        for j in range(len(ports)-1):edge(ports[j],ports[j+1],eid);eid+=1
    for side in('NORTH','EAST','SOUTH','WEST'):
        p=make_port(n,'visible-'+side,names);target=make_port(other,'target-'+side,names);set_side(p,side);all_ports.append(p);edge(p,target,eid);eid+=1
    self_loop_preprocessor(g);holder=n.properties['SELF_LOOP_HOLDER'];_source_sort(n.ports,_compare_ports)
    layer=Layer(g);g.layers.append(layer);set_layer(n,layer);set_layer(other,layer);g.layerless_nodes.clear()
    monitor=BasicProgressMonitor(False,False);self_loop_port_restorer(g,monitor=monitor);restored=[names[p]for p in n.ports];director=RoutingDirector();director.determine_routes(holder)
    results.append({'name':inputs['name'],'restored':restored,'ports':[{'name':names[p],'owner':p.owner is n,'id':p.id,'side':p.side}for p in all_ports],
                    'hidden':[{'name':names[p],'hidden':slp.is_hidden}for p,slp in holder.sl_ports.items()],
                    'portsHidden':holder.are_ports_hidden,'monitorRunning':monitor.is_running(),'penaltiesCleared':director.port_penalties is None,
                    'loops':[{'type':loop.self_loop_type,'ports':[names[p.l_port]for p in loop.sl_ports],
                              'left':names[loop.leftmost_port.l_port],'right':names[loop.rightmost_port.l_port],
                              'occupied':[side for side in _SIDES if side in loop.occupied_port_sides],
                              'groups':[[side,[names[p.l_port]for p in loop.sl_ports_by_side[side]]]for side in loop.sl_ports_by_side]}for loop in holder.sl_hyper_loops]})
raw=json.loads(original.read_text(encoding='utf8'));comparison=diff(raw['value'],results);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':results,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'requestSha256':hashlib.sha256(request.read_bytes()).hexdigest(),'scope':'One new group3 actual pre/restorer/director objects: STACKED, REVERSE_STACKED, SEQUENCED and allfive loop types; visible nonself ports/canonical holder/live owner restoration/shared enum table requests/IDs/clockwise routes. Slot/shape routers and whole layout not claimed.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
