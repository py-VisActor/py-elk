"""PRIVATE_SRC ORACLE NEW_REPORT; one actual new-holder default witness."""
import hashlib,json,os,sys
from pathlib import Path
source,oracle_path,out=map(Path,sys.argv[1:4]);sys.path.insert(0,str(source.resolve()));sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
from pyelk.execution.properties import PropertySnapshot
from pyelk._errors import UnsupportedOptionError
from layout_checks import diff
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
origin=PropertySnapshot({});one=origin.copy();two=origin.copy();pad=one.read_native('padding');other=two.read_native('padding')
enums=one.read_native('nodeSize.options');enums2=two.read_native('nodeSize.options')
actual={'padding':[pad.top,pad.right,pad.bottom,pad.left],'paddingStored':one.has('padding'),'originPaddingAbsent':not origin.has('padding'),
 'paddingIndependent':pad is not other,'paddingCached':one.read_native('padding')is pad,'enumShared':enums is enums2,'enumAbsent':not one.has('nodeSize.options'),
 'aspectNull':one.read_native('aspectRatio')is None,'aspectAbsent':not one.has('aspectRatio'),
 'borderNull':one.read_native('port.borderOffset')is None,'borderAbsent':not one.has('port.borderOffset')}
assert one.read_native('polyomino.fill',0.5)==0.5 and not one.has('polyomino.fill')
try:one.read_native('layered.considerModelOrder.groupModelOrder.cmEnforcedGroupOrders')
except UnsupportedOptionError:pass
else:raise AssertionError('Unknown owner default silently inferred')
payload=[];assert one.read_native('private.list',factory=lambda:payload,materialize=True)is payload and one.has('private.list')
try:one.read_native('private.dict',{'nested':[]})
except ValueError:pass
else:raise AssertionError('Unspecified private object clone semantics were inferred')
oracle=json.loads(oracle_path.read_text('utf-8'));comparison=diff(oracle['observation'],actual)
assert before=={p.relative_to(source).as_posix():sha(p)for p in source.rglob('*.py')}
with out.open('x',encoding='utf-8')as f:json.dump({'passed':comparison['passed'],'comparison':comparison,'actual':actual,'sourceSha256':before,'pid':os.getpid(),'parentPid':os.getppid(),'oracleSha256':sha(oracle_path),'layoutExecuted':False,'fullValidation':False},f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences'])}));raise SystemExit(0 if comparison['passed']else 1)
