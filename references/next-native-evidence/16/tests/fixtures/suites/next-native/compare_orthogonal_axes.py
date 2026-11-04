"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: new axes1/2 callers only."""
import hashlib,json,math,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered import orthogonal_general as scalar
from pyelk.algorithms.layered.orthogonal_axes import routing_generator,_port_x
from pyelk.algorithms.layered.graph import LGraph,LNode,LPort,LEdge,Vec2,set_port_owner,set_source,set_target
from pyelk.algorithms.layered.ports import set_side
from pyelk.algorithms.layered.phases import JavaRandom
from pyelk.execution.node_micro import VectorChain
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_bytes());original=json.loads(original_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path) and original['probeSha256']==sha(Path(__file__).with_name('orthogonal-axes-probe.cjs'))
assert original['actualAxesGenerators'] is True and original['layoutExecuted'] is False
def number(v):return 'NaN' if math.isnan(v) else '-0' if v==0 and math.copysign(1,v)<0 else v
def point(p):return [number(p.x),number(p.y)]
actual=[]
for c in request['cases']:
    graph=LGraph(None,None,None);nodes=[];ports=[];edges=[]
    for i,x in enumerate(c['positions']):
        n=LNode(graph);n.pos=Vec2(-0.0 if i==0 else float(x),float(i*3));nodes.append(n);graph.layerless_nodes.append(n)
        p=LPort();set_port_owner(p,n);set_side(p,('SOUTH'if c['direction']==1 else'NORTH')if i<3 else('NORTH'if c['direction']==1 else'SOUTH'))
        p.pos.x=-0.0;p.anchor.x=-0.0;ports.append(p)
    for a,b in c['links']:
        e=LEdge();set_source(e,ports[a]);set_target(e,ports[b]);edges.append(e)
    existing=VectorChain([Vec2(-7.0,13.0)]);edges[0].properties['JUNCTION_POINTS']=existing
    empty=VectorChain();edges[1].properties['JUNCTION_POINTS']=empty
    graph.properties['RANDOM']=JavaRandom(c['seed']);generator=routing_generator(c['direction'],c['spacing'])
    splits=[];draws=[];old_split=scalar._Generator._split_segments;old_next=JavaRandom.next_int
    def split(self,dependencies,segments):
        count=len(segments);result=old_split(self,dependencies,segments)
        splits.append({'before':count,'after':len(segments),'dependencies':len(dependencies),'threshold':self.critical_threshold});return result
    def next_int(self,bound):draws.append(bound);return old_next(self,bound)
    scalar._Generator._split_segments=split;JavaRandom.next_int=next_int
    try:slots=generator.route(graph,nodes[:3],nodes[3:],c['start'])
    finally:scalar._Generator._split_segments=old_split;JavaRandom.next_int=old_next
    actual.append({'name':c['name'],'slots':slots,'threshold':generator.critical_threshold,'splits':splits,'draws':draws,
        'portCoordinates':[number(_port_x(p))for p in ports],'sourceSide':generator.source_side,'targetSide':generator.target_side,
        'nodes':[point(n.pos)for n in nodes],'edges':[{'bends':[point(p)for p in e.bend_points],'hasJunction':'JUNCTION_POINTS'in e.properties,'junctions':[point(p)for p in e.properties['JUNCTION_POINTS']]if'JUNCTION_POINTS'in e.properties else None}for e in edges],
        'priorNonemptySame':edges[0].properties['JUNCTION_POINTS'] is existing,'priorEmptySame':edges[1].properties['JUNCTION_POINTS'] is empty,'createdCleared':len(generator.created_junctions)==0})
comparison=diff(original['value'],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
        'actualAxesGenerators':True,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
