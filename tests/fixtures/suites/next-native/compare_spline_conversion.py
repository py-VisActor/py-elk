from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,request,original,out=map(Path,sys.argv[1:5]);probe=Path(sys.argv[5]);raw=json.loads(original.read_text(encoding='utf8'))
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86';assert raw['requestSha256']==hashlib.sha256(request.read_bytes()).hexdigest();assert raw['probeSha256']==hashlib.sha256(probe.read_bytes()).hexdigest()
sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.spline_final import calculate_bezier_bend_points
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from layout_checks import diff
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
vec=lambda p:[p.x,p.y];before=hashes();actual=[]
for input in json.loads(request.read_text(encoding='utf8'))['cases']:
 g=LGraph(None,None,None);g.properties=CanonicalPropertyMap()
 def make(spec):
  n=LNode(g);n.properties=CanonicalPropertyMap();n.pos=Vec2(*spec['node']);p=LPort(n);p.properties=CanonicalPropertyMap();n.ports.append(p);set_side(p,spec['side']);p.pos=Vec2(*spec['port']);p.anchor=Vec2(*spec['anchor'])
  if 'ns'in spec:p.properties['SPLINE_NS_PORT_Y_COORD']=spec['ns']
  return p
 source_port=make(input['source']);target=make(input['target']);old_vectors=[];old_values=[];edges=[]
 for i,points in enumerate(input['bends']):
  edge=LEdge(id=i);edge.properties=CanonicalPropertyMap();set_source(edge,source_port);set_target(edge,target)
  for v in points:
   point=Vec2(*v);edge.bend_points.append(point);old_vectors.append(point);old_values.append(vec(point))
  edges.append(edge)
 references=[e.bend_points for e in edges];chain=[edges[i]for i in input['chain']];owner=SimpleNamespace(spline_routing_mode=input['mode']);selected=None if input['survivor']is None else edges[input['survivor']];sentinel=selected.bend_points[0]if selected is not None and input['survivor']not in input['chain']else None
 calculate_bezier_bend_points(owner,chain,selected)
 actual.append({'name':input['name'],'edges':[{'points':[vec(p)for p in e.bend_points],'sameChain':e.bend_points is references[i]}for i,e in enumerate(edges)],'oldVectorsUnchanged':all(vec(p)==old_values[i]for i,p in enumerate(old_vectors)),'externalSurvivorFirstSame':selected.bend_points[0]is sentinel if sentinel is not None else None})
comparison=diff(raw['value'],actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only new conversionhelper3actual prepared objects: conservative alternating3nonemptychains, NS2chain external survivor retainsoldpoint, emptyearlyreturn. ActualCPs/samechain refs/inputvector immutability compared. No Final.process/controls/sloppy/fullpipeline claim, prior Nub/Loop/SG successes not re-executed.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
