"""PRIVATE_SRC ORIGINAL NEW_REPORT; only corrected empty-input call schedule."""
import hashlib,json,sys
from pathlib import Path
source,original_path,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path('scripts').resolve()))
from pyelk.algorithms.layered import rectilinear_hull as module
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads(original_path.read_bytes())
assert original['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert original['probeSha256']==sha(Path(__file__).with_name('recthull-order-probe.cjs'))
calls=[];failed=False;raw_error=None;maximal=module._maximal;concave=getattr(module,'_concave',None)
def observe_maximal(points,quadrant,**kwargs):
    calls.append(['sweep',quadrant]);return maximal(points,quadrant,**kwargs)
def observe_concave(points,quadrant):
    calls.append(['concave',quadrant]);return concave(points,quadrant)
module._maximal=observe_maximal
if concave is not None:module._concave=observe_concave
try:module.RectilinearConvexHull.of([])
except IndexError as error:failed=True;raw_error={'type':type(error).__name__,'message':str(error)}
finally:
    module._maximal=maximal
    if concave is not None:module._concave=concave
actual={'calls':calls,'failed':failed};comparison=diff(original['value'],actual,tolerant=False)
report={'passed':comparison['passed'],'comparison':comparison,'actual':actual,'rawNativeError':raw_error,'sourceSha256':{Path(module.__file__).as_posix():sha(Path(module.__file__))},
    'originalSha256':sha(original_path),'checkerSha256':sha(Path(__file__)),'scope':'Actual empty-input sweep/concave delegate call order only. No replay or rebinding of six earlier geometry cases; exception classes not compared.',
    'layoutExecuted':False,'fullValidation':False}
with out.open('x',encoding='utf8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'calls':calls,'differences':len(comparison['differences'])}))
raise SystemExit(0 if comparison['passed']else 1)
