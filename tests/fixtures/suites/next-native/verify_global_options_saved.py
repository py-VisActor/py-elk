"""FIRST_ORACLE ONE_CORRECTED_ORACLE SAVED_NATIVE NEW_REPORT; no products."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
original,correction,native,out=map(Path,sys.argv[1:5])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a,b,r=(json.loads(p.read_text('utf-8'))for p in(original,correction,native))
assert a['workerSha256']==b['workerSha256']=='275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
assert a['requestSha256']==b['requestSha256']==r['requestSha256']
assert r['oracleSha256']==sha(original)
assert b['selectedCase']=='array-enumset-is-invalid'and len(b['observation'])==1
expected=[b['observation'][0]if row['name']==b['selectedCase']else row for row in a['observation']]
# Only the observer's top_0 -> top projection changes. Native bytes are intact.
delta=diff(a['observation'],expected,tolerant=False)
assert len(delta['differences'])==6 and all('/6/after/'in d['path']and d['path'].endswith(('/top','/top_0'))for d in delta['differences'])
comparison=diff(expected,r['actual'],tolerant=False)
report={'passed':comparison['passed'],'comparison':comparison,'originalRuns':[{'path':str(p),'sha256':sha(p)}for p in(original,correction)],
 'nativeSavedReport':{'path':str(native),'sha256':sha(native)},'firstNativeProcessExitCode':1,
 'originalCases':8,'recapturedAffectedOriginalCases':1,'nativeReexecuted':False,'productsExecuted':0,
 'sourceCorrectionOnly':'Source probe reads actual Insets.top_0; original compiled field leaked before correction.',
 'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'passed':comparison['passed'],'differences':len(comparison['differences']),'productsExecuted':0}))
raise SystemExit(0 if comparison['passed']else 1)
