from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,request,original,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
from pyelk.algorithms.layered.self_loops_general import (SelfLoopHolder,self_loop_preprocessor,self_loop_port_restorer,RoutingDirector,RoutingSlotAssigner,_SIDES)
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.phases import JavaRandom
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
class ObservedProperties(CanonicalPropertyMap):
    def get(self,key,default=None):
        if key=='RANDOM':self.random_reads+=1
        return super().get(key,default)
before=hashes();results=[]
for input in json.loads(request.read_text(encoding='utf8'))['cases']:
    g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();n=LNode(g);n.properties=CanonicalPropertyMap();g.layerless_nodes.append(n);ports=[]
    g.properties['DIRECTION']='RIGHT';n.properties['PORT_CONSTRAINTS']='FIXED_ORDER';n.properties['ORIGINAL_PORT_CONSTRAINTS']='FIXED_ORDER'
    for side in input['sides']:
        p=LPort(n);p.labels=[];p.properties=CanonicalPropertyMap();n.ports.append(p);set_side(p,side);ports.append(p)
    eid=0
    for i,group in enumerate(input['groups']):
        for j in range(len(group)-1):
            e=LEdge(id=eid);eid+=1;e.labels=[];set_source(e,ports[group[j]]);set_target(e,ports[group[j+1]])
            if input['labels']and j==0:e.labels.append(SimpleNamespace(pos=Vec2(),size=Vec2(20+i,4+i),id=0,properties=CanonicalPropertyMap()))
    if input['groups']:self_loop_preprocessor(g);holder=n.properties['SELF_LOOP_HOLDER']
    else:holder=SelfLoopHolder(n)
    layer=Layer(g);g.layers.append(layer);set_layer(n,layer);g.layerless_nodes.clear();self_loop_port_restorer(g);RoutingDirector().determine_routes(holder)
    for loop in holder.sl_hyper_loops:
        if loop.sl_labels is not None:loop.sl_labels.side='NORTH';loop.sl_labels.position=Vec2(0,-8)
    random=JavaRandom(7)if input['groups']else None
    if random is not None:g.properties['RANDOM']=random
    prior=None if random is None else[random.seedhi,random.seedlo];bounds=[]
    if random is not None:
        real_next=random.next_int
        def observe(bound):bounds.append(bound);return real_next(bound)
        random.next_int=observe
    observed=ObservedProperties(g.properties);observed.random_reads=0;g.properties=observed
    assigner=RoutingSlotAssigner();assigner.assign_slots(holder)
    results.append({'name':input['name'],'randomReads':observed.random_reads,'nextIntBounds':bounds,'seedBefore':prior,'seedAfter':None if random is None else[random.seedhi,random.seedlo],
                    'slots':[{'ports':[p.l_port.id for p in loop.sl_ports],'occupied':[side for side in _SIDES if side in loop.occupied_port_sides],
                              'routing':loop.routing_slot,'labelId':None if loop.sl_labels is None else loop.sl_labels.id}for loop in holder.sl_hyper_loops],
                    'slotCount':holder.routing_slot_count,'scratchCleared':assigner.hyper_edge_segments is None and assigner.sl_loop_to_segment is None and assigner.sl_loop_activity is None})
raw=json.loads(original.read_text(encoding='utf8'));comparison=diff(raw['value'],results);assert before==hashes()
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':results,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'requestSha256':hashlib.sha256(request.read_bytes()).hexdigest(),'scope':'Three new actual Slot caller cases with crossing labeled intervals, three-side wrap hyperloops and empty/null RANDOM; source getter read once including empty, exact slots/labels/shared side activity/RNG state/scratch cleanup. Generic cycle chooser math reused from accepted Ortho; this group records no actual nextInt calls and does not claim a new positive chooser witness. No geometric selfloop routers or complete layout.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
