"""ORIGINAL SAVED_NATIVE NEW_REPORT; retain raw failure and separate witnesses."""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('scripts').resolve()))
from layout_checks import diff
original,native,out=map(Path,sys.argv[1:4]);o=json.loads(original.read_text('utf-8'));n=json.loads(native.read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(original)==n['oracleSha256']
raw=diff(o['observation'],n['actual'],tolerant=False)
assert raw==n['comparison']and len(raw['differences'])==23
assert all(d['path'].startswith('/0/')for d in raw['differences'])
per_case=[diff(e,a,tolerant=False)for e,a in zip(o['observation'],n['actual'],strict=True)]
assert all(c['passed']for c in per_case[1:])
def by_identity(row):
    result=copy.deepcopy(row);result['nodes'].sort(key=lambda n:n['id'])
    for group in result['groups']or():
        group['values'].sort();group['keys'].sort(key=lambda key:tuple(key))
    return result
witness=diff([by_identity(v)for v in o['observation']],[by_identity(v)for v in n['actual']],tolerant=False)
assert witness['passed']is True
report={'rawStrictPassed':False,'rawStrictDifferences':raw['differences'],
 'ordinaryCasesStrictPassed':4,'ordinaryCasesTotal':5,'originalIdentityGeometryAndMembershipComparison':witness,
 'normalizationScope':'Only preserve original-node identity while checking geometry, and compare membership of internal enum-hash-dependent key/value order. Original raw23 differences and failed process are retained; this witness does not replace the raw strict gate.',
 'filesSha256':{p.as_posix():sha(p)for p in(original,native)},'productsExecuted':0,
 'wholeAlgorithmAccepted':False,'wholeExternalPlacerConformanceAccepted':False,'fullValidation':False}
with out.open('x',encoding='utf-8')as f:json.dump(report,f,indent=2)
print(json.dumps({'rawStrictPassed':False,'ordinaryCasesStrictPassed':4,'identityGeometryWitnessPassed':True,'productsExecuted':0}))
