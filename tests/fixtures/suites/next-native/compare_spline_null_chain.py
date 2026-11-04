from pathlib import Path
import sys,json,hashlib
from types import SimpleNamespace
source,original,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.absolute()))
from pyelk.algorithms.layered.spline_final import calculate_bezier_bend_points
before={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
try:calculate_bezier_bend_points(SimpleNamespace(),None,None);actual={'threw':False}
except Exception as error:actual={'threw':True,'errorType':type(error).__name__,'errorText':str(error)}
probe=Path(sys.argv[4])if len(sys.argv)>4 else Path(__file__).with_name('spline-null-chain-probe.cjs')
request=Path(sys.argv[5])if len(sys.argv)>5 else Path(__file__).with_name('spline-null-chain-request.json')
raw=json.loads(original.read_text(encoding='utf8'));assert raw['probeSha256']==hashlib.sha256(probe.read_bytes()).hexdigest();assert raw['requestSha256']==hashlib.sha256(request.read_bytes()).hexdigest();assert raw['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert before=={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in source.rglob('*')if p.is_file()and '__pycache__'not in p.parts}
passed=actual['threw']==raw['value']['threw']
out.write_text(json.dumps({'passed':passed,'actual':actual,'expected':raw['value'],'sourceFilesSha256':before,'sourceTreeUnchanged':True,'originalSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'messageParityClaimed':False,'scope':'Only affected null-edgeChain leaf true failure, no valid-list conversion/P5/Final caller repeated. Error strings/classes preserved separately, equivalence claimed only failure rather than swallowed null.'},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':passed,'actual':actual}));raise SystemExit(0 if passed else 1)
