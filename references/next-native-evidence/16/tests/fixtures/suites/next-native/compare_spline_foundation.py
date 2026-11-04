from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,request,original,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from layout_checks import diff
probe=Path(sys.argv[5])if len(sys.argv)>5 else request.with_name('spline-foundation-probe.cjs')
raw_original=json.loads(original.read_text(encoding='utf8'))
assert raw_original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86','fixed worker identity differs'
assert raw_original['probeSha256']==hashlib.sha256(probe.read_bytes()).hexdigest(),'actual probe identity differs'
assert raw_original['requestSha256']==hashlib.sha256(request.read_bytes()).hexdigest(),'actual request identity differs'
from pyelk.algorithms.layered.spline_general import SplineSegment,Dependency,is_between
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();inputs=json.loads(request.read_text(encoding='utf8'));graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap();segments=[];records=[]
for input in inputs['segments']:
 ports=[]
 for i,p in enumerate(input['ports']):
  node=LNode(graph);node.properties=CanonicalPropertyMap();node.type=p['type'];node.pos.y=p['nodeY'];port=LPort(node);node.ports.append(port);port.properties=CanonicalPropertyMap();set_side(port,p['side']);port.id=i;port.pos.y=p['portY'];port.anchor.y=p['anchorY']
  if 'nsY'in p:port.properties['SPLINE_NS_PORT_Y_COORD']=p['nsY']
  ports.append(port)
 edges=[]
 for i,pair in enumerate(input['edges']):
  edge=LEdge(id=i);edge.properties=CanonicalPropertyMap();set_source(edge,ports[pair[0]]);set_target(edge,ports[pair[1]]);edges.append(edge)
 pair_order=None
 if 'single'in input:
  pairs=[SimpleNamespace(first=input['pairSides'][i],second=e)for i,e in enumerate(edges)];pair_order=[p.second.id for p in pairs];segment=SplineSegment.for_hyperedge(ports[input['single']],pairs,input['singleSide'])
 else:segment=SplineSegment(edges[0],*input['sides'])
 segments.append(segment);box=segment.bounding_box;information=[]
 for e in edges:
  x=segment.edge_information.get(e);information.append({'start':x.start_y,'end':x.end_y,'sourceNormal':x.normal_source_node,'targetNormal':x.normal_target_node,'leftInverted':x.inverted_left,'rightInverted':x.inverted_right})
 records.append({'name':input['name'],'pairOrder':pair_order,'left':[p.id for p in segment.left_ports.values()],'right':[p.id for p in segment.right_ports.values()],'edges':[e.id for e in segment.edges.values()],'bounding':[box.x,box.y,box.width,box.height],'center':segment.center_control_point_y,'top':segment.hyper_edge_top_y,'bottom':segment.hyper_edge_bottom_y,'straight':segment.is_straight,'info':information,'initial':{'mark':segment.mark,'rank':segment.rank,'handled':segment.handled,'initialSegment':segment.initial_segment,'lastSegment':segment.last_segment}})
deps=[Dependency(segments[p[0]],segments[p[1]],p[2])for p in inputs['dependencies']]
actual={'segments':records,'dependencies':[{'source':segments.index(d.source),'target':segments.index(d.target),'weight':d.weight}for d in deps],'adjacency':[{'out':[deps.index(d)for d in s.outgoing],'in':[deps.index(d)for d in s.incoming]}for s in segments],'between':[is_between(*p)for p in inputs['between']]}
expected=raw_original['value'];comparison=diff(expected,actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':expected,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only first3 real spline Segment constructors +3dependencies +7isBetween scalar checks. Hyper constructor consumes this distinct3pair encounter order; source true HashSet Pair order observed [0,1,2], native Pair producer/value hash remains separately unimplemented/unclaimed. No ranking/fullP5/finalCP/oldgroup rerun.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
