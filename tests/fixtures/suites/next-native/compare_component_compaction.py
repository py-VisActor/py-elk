"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT: true new CT controller only."""
import hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered import component_compaction as ct
from pyelk.algorithms.layered.cell_layout import Rectangle
from pyelk.algorithms.layered.compaction_graph import CNode,OneDimensionalCompactor
from pyelk.execution.pair_hash import pair_hash_codes
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
request=json.loads(request_path.read_bytes());original=json.loads(original_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path) and original['probeSha256']==sha(Path(__file__).with_name('component-compaction-probe.cjs'))
assert original['actualComponentController'] is True and original['geometryExplicitlySupplied'] is True and original['layoutExecuted'] is False
def number(v):return 'NaN'if math.isnan(v)else('Infinity'if v>0 else'-Infinity')if not math.isfinite(v)else'-0'if v==0 and math.copysign(1,v)<0 else v
def point(v):return [number(v.x),number(v.y)]
def box(v):return list(map(number,(v.x,v.y,v.width,v.height)))
def rectangle(row):return Rectangle(*map(float,row))
class PreparedExtension:
    def __init__(self,item):
        self.side=item['side'];self.rectangle=rectangle(item['rectangle']);self.placeholder=rectangle(item['placeholder'])if item['placeholder']is not None else None
    def get_representor(self):return self.rectangle
    def get_placeholder(self):return self.placeholder
    def get_direction(self):return {'WEST':'LEFT','EAST':'RIGHT','NORTH':'UP','SOUTH':'DOWN'}[self.side]
lock_table=[];sides=('NORTH','EAST','SOUTH','WEST')
for mask in range(16):
    members=[name for i,name in enumerate(sides)if mask&(1<<i)]
    node=CNode(ct.ComponentsToCGraphTransformer(5),Rectangle(0.0,0.0,1.0,1.0));lock=node.lock;ct.set_lock(node,set(members))
    lock_table.append({'sides':members,'values':[lock.left,lock.right,lock.up,lock.down],'same':node.lock is lock})
hashes=[pair_hash_codes(a,b)for a,b in request['pairCodes']];actual=[]
for c in request['cases']:
    components=[];extensions=[]
    for item in c['components']:
        ee=[PreparedExtension(e)for e in item['extensions']];extensions.extend(ee)
        components.append(SimpleNamespace(graph=SimpleNamespace(properties={'EXT_PORT_CONNECTIONS':set(item['sides'])}),rectilinear_convex_hull=[rectangle(row)for row in item['rectangles']],external_extensions=ee))
    controller=ct.OneDimensionalComponentsCompaction(SimpleNamespace(components=components),c['spacing'])
    graph=controller.graph;groups=graph.groups;nodes=graph.nodes;positions=[controller.transformer.old_position.get(x)for x in components];passes=[];calls=[]
    old_pass=ct.OneDimensionalComponentsCompaction._compact_pass;old_compact=OneDimensionalCompactor.compact
    def compact_pass(self):
        value=old_pass(self);passes.append(number(value));return value
    def compact(self):
        calls.append({'direction':self.direction,'nodes':len(self.graph.nodes),'groups':len(self.graph.groups)});return old_compact(self)
    ct.OneDimensionalComponentsCompaction._compact_pass=compact_pass;OneDimensionalCompactor.compact=compact
    try:controller.compact()
    finally:ct.OneDimensionalComponentsCompaction._compact_pass=old_pass;OneDimensionalCompactor.compact=old_compact
    placeholders=controller.transformer.external_placeholder.values()
    actual.append({'name':c['name'],'passes':passes,'calls':calls,'topLeft':point(controller.top_left),'bottomRight':point(controller.bottom_right),'globalOffset':point(controller.transformer.global_offset),'graphSize':point(controller.transformer.graph_size),
        'offsets':[point(controller.get_offset(x))for x in components],'rectangles':[[box(r)for r in x.rectilinear_convex_hull]for x in components],
        'extensions':[{'rect':box(e.rectangle),'hitbox':box(controller.transformer.external_extensions.get(e).second.hitbox)}for e in extensions],
        'placeholders':[{'rect':box(p.second.rect),'hitbox':box(p.second.hitbox),'spacing':number(p.second.individual_spacing),'groupSeparate':p.second.group is not p.first}for p in placeholders],
        'originalPositionsSame':[controller.transformer.old_position.get(x)is positions[i]for i,x in enumerate(components)],
        'listsSame':graph.groups is groups and graph.nodes is nodes,'cleared':[len(groups),len(nodes)],'finished':controller.compactor.finished,'direction':controller.compactor.direction})
comparison=diff({k:original[k]for k in('value','lockTable','pairHashes')},{'value':actual,'lockTable':lock_table,'pairHashes':hashes},tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'lockTable':lock_table,'pairHashes':hashes,
    'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
    'actualComponentController':True,'geometryExplicitlySupplied':True,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
