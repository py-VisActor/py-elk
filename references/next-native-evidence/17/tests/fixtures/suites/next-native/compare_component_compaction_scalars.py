"""PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT; corrected scalar collectors only."""
import hashlib,json,sys
from pathlib import Path
source,request_path,original_path,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered import component_compaction as ct
from pyelk.algorithms.layered.compaction_graph import CNode
from pyelk.algorithms.layered.cell_layout import Rectangle
from pyelk.execution.pair_hash import pair_hash_codes
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads(original_path.read_bytes());request=json.loads(request_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['requestSha256']==sha(request_path) and original['probeSha256']==sha(Path(__file__).with_name('component-compaction-scalars-probe.cjs'))
assert original['actualScalarHelpers'] is True and original['controlledFieldHashCallbacks'] is True and original['controllerExecutions']==0
locks=[];sides=('NORTH','EAST','SOUTH','WEST')
for mask in range(16):
    members=[name for i,name in enumerate(sides)if mask&(1<<i)]
    node=CNode(ct.ComponentsToCGraphTransformer(5),Rectangle(0.0,0.0,1.0,1.0));lock=node.lock;ct.set_lock(node,set(members))
    locks.append({'sides':members,'values':[lock.get(d)for d in('LEFT','RIGHT','UP','DOWN')],'same':node.lock is lock})
hashes=[pair_hash_codes(a,b)for a,b in request['pairCodes']]
assert original['fieldHashCalls']==[v for a,b in request['pairCodes']for v in(['first',a],['second',b])]
actual={'lockTable':locks,'pairHashes':hashes};comparison=diff({k:original[k]for k in actual},actual,tolerant=False)
paths=[source/'pyelk/algorithms/layered/component_compaction.py',source/'pyelk/execution/pair_hash.py']
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceFilesSha256':{p.relative_to(source).as_posix():sha(p)for p in paths},
    'originalSha256':sha(original_path),'requestSha256':sha(request_path),'checkerSha256':sha(Path(__file__)),
    'controllerExecutions':0,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences']),'controllerExecutions':0}))
raise SystemExit(0 if comparison['passed']else 1)
