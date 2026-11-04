from pathlib import Path
import sys,json,hashlib
source,request,original,out=map(Path,sys.argv[1:5]);probe=Path(sys.argv[5]);raw=json.loads(original.read_text(encoding='utf8'))
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert raw['requestSha256']==hashlib.sha256(request.read_bytes()).hexdigest();assert raw['probeSha256']==hashlib.sha256(probe.read_bytes()).hexdigest()
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.spline_general import SplineEdgeRouter
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,Insets,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.execution.diagnostics import BasicProgressMonitor
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();router=SplineEdgeRouter();initial_map=router.edge_to_segment;results=[];old_edge=None
for input in json.loads(request.read_text(encoding='utf8'))['cases']:
 g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();g.properties['EDGE_ROUTING_SPLINES_MODE']=input['mode'];g.properties['RANDOM']=JavaRandom(7);nodes={};ports={};edges=[]
 for node_inputs in input['layers']:
  layer=Layer(g);g.layers.append(layer);width=0.0
  for item in node_inputs:
   n=LNode(g);n.properties=CanonicalPropertyMap();n.type=item.get('type','NORMAL');n.pos.y=item['y'];n.size=Vec2(item['w'],10);n.margin=Insets(1,2.25,1.5,1.5);set_layer(n,layer);width=max(width,item['w']+1.5+2.25);nodes[item['name']]=n
   for side in['WEST','EAST']:
    p=LPort(n);p.properties=CanonicalPropertyMap();n.ports.append(p);set_side(p,side);p.pos=Vec2(0 if side=='WEST'else item['w'],5);p.anchor=Vec2();ports[item['name']+':'+side]=p
  layer.size.x=width
 for i,v in enumerate(input['edges']):
  e=LEdge(id=i);e.properties=CanonicalPropertyMap();set_source(e,ports[v[0]+':'+v[1]]);set_target(e,ports[v[2]+':'+v[3]]);edges.append(e)
 monitor=BasicProgressMonitor(False,False);router.process(g,monitor)
 if old_edge is None:old_edge=edges[0];old_segment=initial_map.get(old_edge)
 all_segments=router.all_segments;node_names={id(v):k for k,v in nodes.items()};port_names={id(v):k for k,v in ports.items()}
 results.append({'name':input['name'],'width':g.size.x,'nodes':[{'name':name,'position':[n.pos.x,n.pos.y]}for name,n in nodes.items()],'start':[e.id for e in router.start_edges],'segments':[{'edges':[e.id for e in s.edges.values()],'box':[s.bounding_box.x,s.bounding_box.y,s.bounding_box.width,s.bounding_box.height],'delta':s.x_delta,'rank':s.rank,'mark':s.mark,'straight':s.is_straight,'west':s.is_west_of_initial_layer,'initial':s.initial_segment,'last':s.last_segment,'sourceNode':node_names.get(id(getattr(s,'source_node',None))),'targetNode':node_names.get(id(getattr(s,'target_node',None))),'sourcePort':port_names.get(id(getattr(s,'source_port',None))),'targetPort':port_names.get(id(getattr(s,'target_port',None)))}for s in all_segments],'routes':[{'id':e.id,'hasChain':'SPLINE_EDGE_CHAIN'in e.properties,'chain':[x.id for x in e.properties['SPLINE_EDGE_CHAIN']]if'SPLINE_EDGE_CHAIN'in e.properties else None,'hasPath':'SPLINE_ROUTE_START'in e.properties,'path':[all_segments.index(s)for s in e.properties['SPLINE_ROUTE_START']]if'SPLINE_ROUTE_START'in e.properties else None}for e in edges],'monitorRunning':monitor.is_running(),'monitorClosed':monitor._closed,'ownerGraphCleared':router.l_graph is None,'samePersistentMap':router.edge_to_segment is initial_map,'oldMappingPreserved':initial_map.get(old_edge)is old_segment})
class ObservedProperties(CanonicalPropertyMap):
 def get(self,key,default=None):self.reads+=1;return super().get(key,default)
empty=LGraph(None,None,None);empty.size.x=123;empty.properties=ObservedProperties();empty.properties.reads=0;monitor=BasicProgressMonitor(False,False);router.process(empty,monitor)
actual={'cases':results,'empty':{'width':empty.size.x,'optionReads':empty.properties.reads,'running':monitor.is_running(),'closed':monitor._closed,'oldMapPreserved':router.edge_to_segment is initial_map,'oldValuePreserved':initial_map.get(old_edge)is old_segment}}
comparison=diff(raw['value'],actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only new actual P5 SplineEdgeRouter.process2graphs (Conservative hyper/crossing, Sloppy3layers/realLONG_EDGE successor chain+in-layer edge) and empty0optionReads earlyreturn; samecachedOwner/map retained/ownergraph successcleanup. No FinalCP/fullAPI; prior successful gap/SG3rank/3foundation/Loop/Nub objects not re-executed.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
