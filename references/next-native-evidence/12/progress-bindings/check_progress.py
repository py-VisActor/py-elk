"""Source-only immutable batch12 evidence/limited review bindings; no layouts."""
import hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'docs/changes/20261104-next-native-12.json';record=json.loads(p.read_text('utf-8'))
for item in record['evidence'].values():assert sha(root/item['path'])==item['sha256'],item['path']
assert sha(root/'docs/changes'/record['previousProgressRecord'])==record['previousProgressRecordSha256']
cp=record['checkpoint'];assert sha(root/cp['path'])==cp['sha256']
m=json.loads((root/cp['path']).read_text('utf-8'));tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==138
assert sha(root/m['baseArchive'])==m['baseArchiveSha256']
with zipfile.ZipFile(root/m['baseArchive'])as archive:
    for name,value in m['baseFilesSha256'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==value
for name,item in m['overrides'].items():
    assert sha(root/'migration/next-native/objects'/(item['sha256']+'.bin'))==tree[name]==item['sha256']
matched={}
for review in record['reviewScopes']:
    assert review['doesNotApproveWholeModule']is True and sha(root/review['path'])==review['sha256']
    raw=json.loads((root/review['path']).read_text('utf-8'));assert raw['accepted']is True and raw['blockers']==[]
    bindings={path.replace('\\','/'):value for path,value in raw['filesSha256'].items()}
    for name,value in review['matchingCheckpointFiles'].items():
        assert tree[name]==value and any(path.endswith('/src/pyelk/'+name)and digest==value for path,digest in bindings.items())
        matched[name]=value
required=('execution/metadata_service.py','metadata/_registration_data.py',
 'execution/local_properties.py','execution/node_micro.py','execution/json_transfer.py','execution/recursive.py',
 'algorithms/layered/network_simplex_general.py','algorithms/layered/brandes_koepf_general.py',
 'algorithms/layered/orthogonal_general.py','algorithms/layered/native_properties.py',
 'algorithms/layered/layout_configuration.py','algorithms/layered/algorithm_assembler.py',
 'algorithms/layered/diagnostic_strings.py','algorithms/layered/input_model_sort.py','algorithms/layered/property_access.py')
assert all(name in matched for name in required),[name for name in required if name not in matched]
plan=json.loads((root/'docs/iteration-plan.json').read_text('utf-8'))
assert plan['validationPolicy']['featureImplementationComplete']is False
assert plan['parallelPreparation']['codeCheckpoint']==cp
assert plan['parallelPreparation']['progressRecord'].endswith('next-native-12.json')
assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==record['wholeAlgorithmsAccepted']==0
assert record['metadataRegistration']['newOriginalRegistrationGroups']==11
assert record['metadataRegistration']['newSelectedBoxIntegrationRequests']==2
assert record['generalNetworkSimplex']['newWorkingGraphCases']==4
assert record['generalBrandesKoepf']['initialNativeExitCode']==1
assert record['generalBrandesKoepf']['wholeSevenCaseProcessRerun']is False
assert record['generalOrthogonal']['numericControlsAreGeometryPass']is False
assert record['fullValidation']is False and record['publicAPIIntegrated']is False
print(json.dumps({'passed':True,'scope':'immutable138 source and archived evidence/review file bindings; limited scope only',
 'evidenceFiles':len(record['evidence']),'reviewScopes':len(record['reviewScopes']),
 'matchingSourceBindings':len(matched),'productsExecuted':0,'fullValidation':False}))
