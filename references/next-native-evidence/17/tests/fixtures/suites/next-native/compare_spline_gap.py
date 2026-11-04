from pathlib import Path
import sys,json,hashlib
source,request,original,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
raw=json.loads(original.read_text(encoding='utf8'));probe=Path(sys.argv[5])if len(sys.argv)>5 else request.with_name('spline-gap-probe.cjs')
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert raw['probeSha256']==hashlib.sha256(probe.read_bytes()).hexdigest()
assert raw['requestSha256']==hashlib.sha256(request.read_bytes()).hexdigest()
from pyelk.algorithms.layered.spline_general import SplineEdgeRouter
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Layer,Vec2,set_source,set_target,set_layer
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.phases import JavaRandom
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();router=SplineEdgeRouter();mapping=router.edge_to_segment;records=[];old_edge=None
for input in json.loads(request.read_text(encoding='utf8'))['cases']:
 g=LGraph(None,None,None);g.properties=CanonicalPropertyMap();left=Layer(g);right=Layer(g);g.layers.extend((left,right));ports=[];edges=[];left.size.x=40.5;right.size.x=35.25
 for i in range(6):
  n=LNode(g);n.properties=CanonicalPropertyMap();n.id=i;n.pos.y=([0,60,100][i]if i<3 else[20,50,110][i-3])+input['shift'];n.size=Vec2(20,10);layer=left if i<3 else right;set_layer(n,layer);p=LPort(n);p.properties=CanonicalPropertyMap();n.ports.append(p);set_side(p,'EAST'if i<3 else'NORTH'if i==3 else'WEST');p.id=i;p.pos.y=5;p.anchor.y=0;ports.append(p)
  if i==3:p.properties['SPLINE_NS_PORT_Y_COORD']=85+input['shift']
 for i,pair in enumerate([[0,3],[0,4],[1,5],[2,5],[4,2],[1,2]]):
  e=LEdge(id=i);e.properties=CanonicalPropertyMap();set_source(e,ports[pair[0]]);set_target(e,ports[pair[1]])
  if i==4:e.properties['REVERSED']=input['reversed']
  edges.append(e)
 g.properties['GRAPH_PROPERTIES']=set(input['flags']);config=router.get_layout_processor_configuration(g);configuration=[[p.name for p in sorted(values,key=lambda p:p.ordinal)]for values in config.list]
 g.properties['RANDOM']=JavaRandom(7);router.l_graph=g;router.start_edges.clear();router.all_segments.clear();router.successor.clear();router.clear_then_fill(left,right);router.create_segments_and_ranking()
 if old_edge is None:old_edge=edges[0];old_segment=mapping.get(old_edge);old_code=router.identity_hash(old_edge)
 segments=router.segments_layer
 def dep(d):return{'source':segments.index(d.source),'target':segments.index(d.target),'weight':d.weight}
 records.append({'name':input['name'],'configuration':configuration,'leftPorts':[p.id for p in router.left_ports_layer.values()],'rightPorts':[p.id for p in router.right_ports_layer.values()],'remaining':[e.id for e in router.remaining_edges],'start':[e.id for e in router.start_edges],'segments':[{'edges':[e.id for e in s.edges.values()],'left':[p.id for p in s.left_ports.values()],'right':[p.id for p in s.right_ports.values()],'box':[s.bounding_box.y,s.bounding_box.height],'top':s.hyper_edge_top_y,'bottom':s.hyper_edge_bottom_y,'center':s.center_control_point_y,'straight':s.is_straight,'mark':s.mark,'rank':s.rank,'out':[dep(d)for d in s.outgoing],'in':[dep(d)for d in s.incoming]}for s in segments],'successors':[None if router.successor.get(e)is None else router.successor.get(e).id for e in edges],'reversed':[{'has':'REVERSED'in e.properties,'value':e.properties.get('REVERSED')if e.properties.get('REVERSED')is not None else False}for e in edges],'sameMap':router.edge_to_segment is mapping,'oldMappingPreserved':mapping.get(old_edge)is old_segment,'oldHashStable':router.identity_hash(old_edge)==old_code,'newSameIdDifferentObject':edges[0]is not old_edge})
comparison=diff(raw['value'],records);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':records,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'originalIdentityEvidence':raw['identityEvidence'],'nativeIdentityEvidence':{'oldFirstCode':old_code,'oldLastCode':router.identity_hash(old_edge)},'identityCodeParityClaimed':False,'scope':'Only new actual gap collect/4hyperpasses/ordinarysegments/dependency/ranking across2 prepared graphs on same cached owner, mixed reversed and NS privateY!=absoluteY, in-layer edge, allFlags configuration query. Data+old-map/actual first-code stability exact; GWT numeric code values separately retained/native policy not equated. Main P5/FinalCP and prior3ranking/3foundation controls not re-executed.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
