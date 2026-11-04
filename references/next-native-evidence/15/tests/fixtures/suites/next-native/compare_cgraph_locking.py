"""PRIVATE_SRC ORIGINAL NEW_REPORT: actual locking callback evaluation order."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from pyelk.algorithms.layered.compaction_graph import CGraph,CNode,OneDimensionalCompactor
from pyelk.algorithms.layered.cell_layout import Rectangle
from layout_checks import diff
graph=CGraph({'UNDEFINED','LEFT','RIGHT','UP','DOWN'});node=CNode(SimpleNamespace(spacing=1),Rectangle(0,0,1,1));graph.nodes.append(node)
compactor=OneDimensionalCompactor(graph);calls=0
def locking(pair):
    global calls
    calls+=1
    if calls==2:pair[0].group.reposition=False
    return True
compactor.set_locking_strategy(locking).apply_locking_strategy()
actual={'calls':calls,'nodeReposition':node.reposition,'groupReposition':node.group.reposition,
        'groupValueType':'boolean'if type(node.group.reposition)is bool else'number'}
raw=json.loads(original.read_bytes());assert raw['controlledCallbackSideEffect']is True
comparison=diff(raw['value'],actual,tolerant=False);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert raw['probeSha256']==sha(Path(__file__).with_name('cgraph-locking-probe.cjs'))
with out.open('x',encoding='utf8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,
 'sourceFilesSha256':{'pyelk/algorithms/layered/compaction_graph.py':sha(source/'pyelk/algorithms/layered/compaction_graph.py')},
 'originalSha256':sha(original),'checkerSha256':sha(Path(__file__)),'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
