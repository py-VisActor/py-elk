from pathlib import Path
import sys,json,hashlib
source,request,original,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.absolute()));sys.path.insert(0,str(Path('scripts').absolute()))
from pyelk.algorithms.layered.spline_general import SplineSegment,Dependency,break_cycles,topological_numbering
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,set_source,set_target
from pyelk.algorithms.layered.native_properties import CanonicalPropertyMap
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.phases import JavaRandom
from layout_checks import diff
raw=json.loads(original.read_text(encoding='utf8'));probe=Path(sys.argv[5])if len(sys.argv)>5 else request.with_name('spline-ranking-probe.cjs')
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert raw['probeSha256']==hashlib.sha256(probe.read_bytes()).hexdigest()
assert raw['requestSha256']==hashlib.sha256(request.read_bytes()).hexdigest()
def hashes():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
before=hashes();actual=[]
for input in json.loads(request.read_text(encoding='utf8'))['cases']:
 graph=LGraph(None,None,None);graph.properties=CanonicalPropertyMap();segments=[]
 for i,left in enumerate(input['left']):
  a=LNode(graph);b=LNode(graph);p=LPort(a);q=LPort(b);a.ports.append(p);b.ports.append(q);p.properties=CanonicalPropertyMap();q.properties=CanonicalPropertyMap();set_side(p,'EAST');set_side(q,'WEST');p.pos.y=i*10;q.pos.y=i*10+5;e=LEdge();set_source(e,p);set_target(e,q);segments.append(SplineSegment(e,'LEFT'if left else'RIGHT','RIGHT'))
 dependencies=[Dependency(segments[p[0]],segments[p[1]],p[2])for p in input['dependencies']];random=JavaRandom(input['seed']);prior=[random.seedhi,random.seedlo];bounds=[];real_next=random.next_int
 def observe(bound):bounds.append(bound);return real_next(bound)
 random.next_int=observe;break_cycles(segments,random);after_cycle=[{'mark':s.mark,'inWeight':s.in_weight,'outWeight':s.out_weight}for s in segments];topological_numbering(segments)
 actual.append({'name':input['name'],'nextIntBounds':bounds,'seedBefore':prior,'seedAfter':[random.seedhi,random.seedlo],'afterCycle':after_cycle,'segments':[{'mark':s.mark,'rank':s.rank,'inWeight':s.in_weight,'outWeight':s.out_weight,'out':[dependencies.index(d)for d in s.outgoing],'in':[dependencies.index(d)for d in s.incoming]}for s in segments],'dependencies':[{'source':segments.index(d.source),'target':segments.index(d.target),'weight':d.weight,'active':any(x is d for x in d.source.outgoing)and any(x is d for x in d.target.incoming)}for d in dependencies]})
comparison=diff(raw['value'],actual);assert hashes()==before
out.write_text(json.dumps({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'scope':'Only new actual spline weighted breakCycles/topologicalNumbering prepared graph 3cases: weighted DAG, tied cycle and unique chooser bound1. Real shared JavaRandom actual bounds/state observed; in/out encounter/cycle marks/reversed positive/dropzero/degrees/ranks all compared. No spline driver/finalCP/oldobjectgroup execution.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
