"""Immutable batch14 source/evidence and limited review bindings; zero products."""
import hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'docs/changes/20261104-next-native-14.json';record=json.loads(p.read_bytes())
for item in record['evidence'].values():assert sha(root/item['path'])==item['sha256'],item['path']
assert sha(root/'docs/changes'/record['previousProgressRecord'])==record['previousProgressRecordSha256']
cp=record['checkpoint'];assert sha(root/cp['path'])==cp['sha256']
m=json.loads((root/cp['path']).read_bytes());tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==154
assert sha(root/m['baseArchive'])==m['baseArchiveSha256']
with zipfile.ZipFile(root/m['baseArchive'])as archive:
    for name,value in m['baseFilesSha256'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==value
for name,item in m['overrides'].items():
    assert sha(root/'migration/next-native/objects'/(item['sha256']+'.bin'))==tree[name]==item['sha256']
matched={}
for review in record['reviewScopes']:
    assert review['doesNotApproveWholeModule']is True and sha(root/review['path'])==review['sha256']
    raw=json.loads((root/review['path']).read_bytes());assert raw['accepted']is True and raw['blockers']==[]
    bindings={path.replace('\\','/'):value for path,value in raw['filesSha256'].items()}
    for name,value in review['matchingCheckpointFiles'].items():
        assert tree[name]==value and any(path.endswith('/src/pyelk/'+name)and digest==value for path,digest in bindings.items())
        matched[name]=value
required=('execution/enum_identity.py','execution/enum_collections.py',
          'algorithms/layered/native_adapters.py','algorithms/layered/component_groups.py')
assert all(name in matched for name in required),[name for name in required if name not in matched]
plan=json.loads((root/'docs/iteration-plan.json').read_bytes())
assert plan['validationPolicy']['featureImplementationComplete']is False
assert plan['parallelPreparation']['codeCheckpoint']==cp
assert plan['parallelPreparation']['progressRecord'].endswith('next-native-14.json')
assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==record['wholeAlgorithmsAccepted']==0
assert record['layeredComponents']['rawStrictDifferences']==23
assert record['layeredComponents']['ordinaryCasesStrictPassed']==4
assert record['layeredComponents']['wholeExternalConformanceAccepted']is False
assert record['layeredDefault']['firstFullNativeExecuted']is False
assert record['projectLicense']['userSelectedOriginalCode']=='MIT'
assert record['projectLicense']['allFilesIndependentlyRewrittenClaimEstablished']is False
assert record['fullValidation']is False and record['publicAPIIntegrated']is False
print(json.dumps({'passed':True,'scope':'immutable154 source and archived evidence/review file bindings; limited only',
 'evidenceFiles':len(record['evidence']),'reviewScopes':len(record['reviewScopes']),
 'matchingSourceBindings':len(matched),'productsExecuted':0,'fullValidation':False}))
