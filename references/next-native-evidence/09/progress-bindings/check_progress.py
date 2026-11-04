"""Source-only archive verification. No product imports or layout execution."""
import hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'docs/changes/20261104-next-native-09.json';record=json.loads(p.read_text('utf-8'))
for item in record['evidence'].values():assert sha(root/item['path'])==item['sha256'],item['path']
assert sha(root/'docs/changes'/record['previousProgressRecord'])==record['previousProgressRecordSha256']
cp=record['checkpoint'];assert sha(root/cp['path'])==cp['sha256']
m=json.loads((root/cp['path']).read_text('utf-8'));tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==99
assert sha(root/m['baseArchive'])==m['baseArchiveSha256']
with zipfile.ZipFile(root/m['baseArchive'])as archive:
    for name,digest in m['baseFilesSha256'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest
for name,item in m['overrides'].items():
    assert sha(root/'migration/next-native/objects'/(item['sha256']+'.bin'))==tree[name]==item['sha256'],name
matched={}
for review in record['reviewScopes']:
    assert sha(root/review['path'])==review['sha256']
    raw=json.loads((root/review['path']).read_text('utf-8'));assert raw['accepted']is True and not raw['blockers']
    bindings={path.replace('\\','/'):value for path,value in raw['filesSha256'].items()}
    for name,value in review['matchingCheckpointFiles'].items():
        assert tree[name]==value and any(path.endswith('/src/pyelk/'+name)and digest==value for path,digest in bindings.items())
        matched[name]=value
required=('execution/json_transfer.py','execution/node_micro.py','execution/properties.py','algorithms/fixed.py','algorithms/box.py')
assert all(name in matched for name in required),[name for name in required if name not in matched]
plan=json.loads((root/'docs/iteration-plan.json').read_text('utf-8'))
assert plan['validationPolicy']['featureImplementationComplete']is False
assert plan['parallelPreparation']['progressRecord'].endswith('next-native-09.json')
assert plan['parallelPreparation']['codeCheckpoint']==cp
assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==record['wholeAlgorithmsAccepted']==0
assert all(x['status']=='planned'for x in plan['iterations']if x['id']in record['officialIterationsRemainPlanned'])
assert record['hostDelta']['integerGuardNegativeControls']==5 and record['hostDelta']['integerGuardPositiveControls']==1
assert record['fullValidation']is False and record['publicAPIIntegrated']is False
print(json.dumps({'passed':True,'scope':'fixed99 immutable source / archived receipt bytes / scope-limited accepted review bindings',
 'evidenceFiles':len(record['evidence']),'matchingSourceReviewBindings':len(matched),'reviewScopes':len(record['reviewScopes']),
 'productExecuted':False,'fullValidation':False,'wholeAlgorithmsAccepted':0}))
