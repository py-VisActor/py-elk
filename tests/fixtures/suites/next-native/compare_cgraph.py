"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT [CASE_INDEX ...]: new CGraph objects."""
import hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
selected=[int(value)for value in sys.argv[5:]]
from layout_checks import diff
from pyelk.algorithms.layered.cell_layout import Rectangle
from pyelk.algorithms.layered.compaction_graph import CGraph,CNode,CGroup,OneDimensionalCompactor,ComponentSpacing,_SCANLINE_CONSTRAINTS
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
def number(x):
    if not math.isfinite(x):return {'number':'NaN'if math.isnan(x)else'Infinity'if x>0 else'-Infinity'}
    if x==0 and math.copysign(1,x)<0:return {'number':'-0'}
    return x
actual=[];cases=json.loads(request_path.read_bytes())['cases']
selected=list(range(len(cases)))if not selected else selected
assert len(selected)==len(set(selected))and all(0<=i<len(cases)for i in selected)
for inputs in (cases[i]for i in selected):
    graph=CGraph({'UNDEFINED','LEFT','RIGHT','UP','DOWN'});owner=SimpleNamespace(spacing=inputs['spacing'])
    nodes=[CNode(owner,Rectangle(*row),inputs['individualSpacing'][i])for i,row in enumerate(inputs['rectangles'])];graph.nodes.extend(nodes)
    for indices in inputs['groups']:graph.groups.append(CGroup(nodes[i]for i in indices))
    compactor=OneDimensionalCompactor(graph);calls=[];observations=[]
    if inputs['componentSpacing']:compactor.set_spacings_handler(ComponentSpacing())
    if inputs['locking']:
        def locking(pair):
            node,direction=pair;calls.append([nodes.index(node),direction])
            return inputs['locking'][(len(calls)-1)%len(inputs['locking'])]
        compactor.set_locking_strategy(locking)
    def snapshot(label):
        return {'label':label,'direction':compactor.direction,'finished':compactor.finished,
          'nodes':[{'id':n.id,'box':list(map(number,(n.hitbox.x,n.hitbox.y,n.hitbox.width,n.hitbox.height))),
            'offset':list(map(number,(n.group_offset.x,n.group_offset.y))),
            'constraints':[nodes.index(v)for v in n.constraints],'reposition':n.reposition,
            'start':number(n.start_pos),'group':graph.groups.index(n.group)}for n in nodes],
          'groups':[{'nodes':[nodes.index(n)for n in g.nodes],'reference':None if g.reference is None else nodes.index(g.reference),
            'incoming':[nodes.index(n)for n in g.incoming_constraints.values()],'outDegree':g.out_degree,
            'delta':number(g.delta),'normalized':number(g.delta_normalized),'start':number(g.start_pos),
            'reposition':g.reposition,'repositionType':'boolean'if type(g.reposition)is bool else'number'}for g in graph.groups]}
    observations.append(snapshot('constructed'))
    for direction in inputs['directions']:
        compactor.change_direction(direction);observations.append(snapshot('changed-'+direction))
        compactor.apply_locking_strategy();observations.append(snapshot('locked-'+direction))
        compactor.compact();observations.append(snapshot('compacted-'+direction))
    compactor.finish();observations.append(snapshot('finished'))
    actual.append({'name':inputs['name'],'calls':calls,'observations':observations,
                   'usesSharedCalculator':compactor.constraint_algorithm is _SCANLINE_CONSTRAINTS})
original=json.loads(original_path.read_bytes());assert original['requestSha256']==sha(request_path)
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['probeSha256']==sha(Path(__file__).with_name('cgraph-probe.cjs'))
assert original['actualCGraphEngine']is True and original['controlledLockingCallback']is True
comparison=diff([original['value'][i]for i in selected],actual,tolerant=False)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
    'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':sha(original_path),'requestSha256':sha(request_path),
    'checkerSha256':sha(Path(__file__)),'selectedCaseIndexes':selected,'scope':'New actual general CGraph engine only; no RectHull/connected transformer/full layout.',
    'controlledLockingCallback':True,'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'cases':len(actual),'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
