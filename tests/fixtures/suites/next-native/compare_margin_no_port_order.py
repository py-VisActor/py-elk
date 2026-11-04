"""PRIVATE_SRC ORIGINAL NEW_REPORT; only common numeric leaf regression."""
import hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
from pyelk.algorithms.layered.native_adapters import _compute_label_box
from pyelk.algorithms.layered.graph import Vec2
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
node=SimpleNamespace(pos=Vec2(1e16,3),size=Vec2(1,4));label=SimpleNamespace(size=Vec2(1,2))
actual=[{'incoming':incoming,'box':_compute_label_box(label,incoming,node,None,None,1)}for incoming in(True,False)]
raw=json.loads(original.read_text('utf-8'));comparison=diff(raw['value'],actual,tolerant=False)
module=source/'pyelk/algorithms/layered/native_adapters.py'
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'expected':raw['value'],
 'sourceFilesSha256':{module.relative_to(source).as_posix():sha(module)},'originalSha256':sha(original),
 'checkerSha256':sha(Path(__file__)),'originalReexecuted':False,'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
