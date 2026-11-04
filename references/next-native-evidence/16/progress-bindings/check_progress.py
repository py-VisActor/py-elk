"""Immutable batch16 source/evidence and explicit limited review bindings."""
import hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'docs/changes/20261104-next-native-16.json';record=json.loads(p.read_bytes())
for item in record['evidence'].values():assert sha(root/item['path'])==item['sha256'],item['path']
assert sha(root/'docs/changes'/record['previousProgressRecord'])==record['previousProgressRecordSha256']
cp=record['checkpoint'];assert sha(root/cp['path'])==cp['sha256']
m=json.loads((root/cp['path']).read_bytes());tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==171
assert sha(root/m['baseArchive'])==m['baseArchiveSha256']
with zipfile.ZipFile(root/m['baseArchive'])as archive:
    for name,value in m['baseFilesSha256'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==value
for name,item in m['overrides'].items():
    assert sha(root/'migration/next-native/objects'/(item['sha256']+'.bin'))==tree[name]==item['sha256']
matched={}
for review in record['reviewScopes']:
    assert review['doesNotApproveWholeModule'] is True and sha(root/review['path'])==review['sha256']
    raw=json.loads((root/review['path']).read_bytes());assert raw['accepted'] is True and raw['blockers']==[]
    bindings={path.replace('\\','/'):value for path,value in raw['filesSha256'].items()}
    for name,value in review['matchingCheckpointFiles'].items():
        assert tree[name]==value and any(path.endswith('/src/pyelk/'+name) and digest==value for path,digest in bindings.items())
        matched[name]=value
def review(suffix):
    rows=[r for r in record['reviewScopes']if r['path'].endswith(suffix)];assert len(rows)==1
    return json.loads((root/rows[0]['path']).read_bytes())
required=('native_import_hierarchical.py','compound_model.py','compound_pre.py','compound_post.py',
    'external_port_dummy.py','hierarchical_resize.py','phase_factories.py','rectilinear_hull.py','orthogonal_axes.py')
assert all('algorithms/layered/'+name in matched for name in required)
for suffix in ('V/compound-pre-post-code-review-01.json','V/hierarchical-import-code-review-01.json',
    'V/hierarchical-driver-code-review-01.json','V/orthogonal-axes-code-review-01.json','V/recthull-code-review-01.json',
    'V/spline-foundation-code-review-01.json','V/spline-ranking-code-review-01.json',
    'root/hierarchical-node-resizer-code-review-01/review.json','root/hierarchical-resizer-factory-code-review-01/review.json'):
    review(suffix)
# The reviewer froze this one module outside a src tree. Bind its actual hash
# explicitly; its source bytes remain recoverable in the checkpoint objects.
driver=review('V/hierarchical-driver-code-review-01.json')
assert tree['algorithms/layered/hierarchical_driver.py']==driver['filesSha256']['.local/v-hierarchical-driver-review-01/hierarchical_driver.py']
plan=json.loads((root/'docs/iteration-plan.json').read_bytes())
assert plan['validationPolicy']['featureImplementationComplete'] is False
assert plan['parallelPreparation']['codeCheckpoint']==cp
assert plan['parallelPreparation']['progressRecord'].endswith('next-native-16.json')
assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==record['wholeAlgorithmsAccepted']==0
assert record['hierarchy']['compoundGeometryExplicitlySupplied'] is True
assert record['hierarchy']['fullCompoundConsumerExecuted'] is False
assert record['generalSpline']['mainDriverIncludedAsUnexecutedDraft'] is True
assert record['generalSpline']['gapFirstNativeRawStrictPassed'] is False
assert record['rectilinearHull']['sixCasesReexecutedAfterScheduleFix'] is False
assert record['rectilinearHull']['exceptionClassOrTextEquivalenceClaimed'] is False
assert record['orthogonalAxes']['oldDirectionZeroGroupsReexecuted'] is False
assert record['connectedCompaction']['fullConnectedCompactorImplemented'] is False
assert record['fullValidation'] is False and record['publicAPIIntegrated'] is False
print(json.dumps({'passed':True,'scope':'immutable171 source/evidence and named limited review bindings only',
    'evidenceFiles':len(record['evidence']),'reviewScopes':len(record['reviewScopes']),
    'matchingSourceBindings':len(matched),'productsExecuted':0,'fullValidation':False}))
