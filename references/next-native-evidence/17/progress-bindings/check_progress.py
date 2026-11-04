"""Verify batch17 immutable source/evidence and limited reviews; no layouts."""
import hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'docs/changes/20261104-next-native-17.json';record=json.loads(p.read_bytes())
for item in record['evidence'].values():assert sha(root/item['path'])==item['sha256'],item['path']
assert sha(root/'docs/changes'/record['previousProgressRecord'])==record['previousProgressRecordSha256']
cp=record['checkpoint'];assert sha(root/cp['path'])==cp['sha256']
m=json.loads((root/cp['path']).read_bytes());tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==183
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
required=('component_compaction.py','connected_compactor.py','hierarchical_port_constraints.py',
 'hierarchical_port_size.py','hierarchical_port_position.py','hierarchical_port_ortho.py','directions_general.py',
 'graph.py','inverted_ports_general.py','provider.py','phase_factories.py','spline_general.py','spline_final.py')
assert all('algorithms/layered/'+name in matched for name in required),sorted(set(required)-{n.rsplit('/',1)[-1]for n in matched})
assert tree['algorithms/layered/spline_general.py']=='056fdf8dad050391646dd36757d09d8b0ead819392f48bd553218f3602b6b47e'
assert tree['algorithms/layered/spline_final.py']=='bbe48547a143bfde736d673efcd436d3d6da5ba514b90816edc83f307406831e'
assert tree['algorithms/layered/polyline_general.py']=='213b6e4d8f2ad51903b82bfb1854d7734f5cce6311c690d8e109059bfd1fec03'
for suffix in('V/component-controller-code-review-01.json','V/connected-compactor-code-review-01.json',
 'V/compound-caller-code-review-01.json','V/hierarchy-projection-code-review-01.json',
 'V/hierarchy-port-phases-code-review-01.json','V/general-direction-code-review-01.json',
 'V/down-direction-caller-code-review-01.json','root/spline-main-code-review-01/review.json',
 'root/spline-final-code-review-01/review.json'):
    assert sum(r['path'].endswith(suffix)for r in record['reviewScopes'])==1,suffix
assert record['hierarchy']['fullCompoundConsumerExecuted']is True
assert record['hierarchy']['fullCompoundRawGeneratedShapeHashDifferences']==7
assert record['hierarchy']['oldShallowProjectionRemainingDifferences']==4
assert record['generalDirections']['oldDirectionMatrixReexecuted']is False
assert record['generalSpline']['loggingTrueCandidateGateActualEngineCalls']==0
assert record['generalSpline']['wholeSplineAccepted']is False
assert record['connectedCompaction']['sourceReturnValBugRepaired']is False
assert record['connectedCompaction']['oldExternalIdentityOrderRaw23GapClosed']is False
assert record['wholeAlgorithmsAccepted']==0
assert all(record[k]is False for k in('fullValidation','publicAPIIntegrated','installedPackageValidated','packagePublished'))
plan=json.loads((root/'docs/iteration-plan.json').read_bytes());assert plan['validationPolicy']['featureImplementationComplete']is False
active=plan['parallelPreparation']['progressRecord'].endswith('next-native-17.json')
if active:assert plan['parallelPreparation']['codeCheckpoint']==cp
print(json.dumps({'passed':True,'scope':'immutable183 source/evidence and limited named review bindings only',
 'evidenceFiles':len(record['evidence']),'reviewScopes':len(record['reviewScopes']),
 'matchingSourceBindings':len(matched),'activePlanStillBatch17':active,'productsExecuted':0,'fullValidation':False}))
