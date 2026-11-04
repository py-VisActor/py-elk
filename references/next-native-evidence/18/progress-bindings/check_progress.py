"""Immutable batch18 source/evidence and limited actual caller bindings."""
import hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=root/'docs/changes/20261104-next-native-18.json';record=json.loads(p.read_bytes())
for item in record['evidence'].values():assert sha(root/item['path'])==item['sha256'],item['path']
assert sha(root/'docs/changes'/record['previousProgressRecord'])==record['previousProgressRecordSha256']
cp=record['checkpoint'];assert sha(root/cp['path'])==cp['sha256']
m=json.loads((root/cp['path']).read_bytes());tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==191
assert sha(root/m['baseArchive'])==m['baseArchiveSha256']
with zipfile.ZipFile(root/m['baseArchive'])as archive:
 for name,value in m['baseFilesSha256'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==value
for name,item in m['overrides'].items():assert sha(root/'migration/next-native/objects'/(item['sha256']+'.bin'))==tree[name]==item['sha256']
matched={}
for review in record['reviewScopes']:
 assert review['doesNotApproveWholeModule']is True and sha(root/review['path'])==review['sha256']
 r=json.loads((root/review['path']).read_bytes());assert r['accepted']is True and r['blockers']==[]
 bindings={path.replace('\\','/'):value for path,value in r['filesSha256'].items()}
 for name,value in review['matchingCheckpointFiles'].items():
  assert tree[name]==value and any(path.endswith('/src/pyelk/'+name)and digest==value for path,digest in bindings.items())
  matched[name]=value
required=('polyline_general.py','longest_path_general.py','simple_placement.py','cycles_general.py',
 'reversed_edges_general.py','center_label_dummies.py','center_label_switcher.py','label_side_selector.py',
 'label_management_general.py','end_label_placement.py','phase_factories.py')
assert all('algorithms/layered/'+name in matched for name in required),[name for name in required if'algorithms/layered/'+name not in matched]
for suffix in('root/polyline-code-review-01/review.json','root/longest-path-code-review-01/review.json',
 'root/simple-placement-code-review-01/review.json','B/depth-first-code-review-01/review.json',
 'root/general-restorer-code-review-01/review.json','root/end-label-placement-code-review-01/review.json',
 'V/center-label-lifecycle-code-review-01.json','V/label-side-selector-code-review-01.json',
 'V/label-switcher-code-review-01.json','V/polyline-caller-code-review-01.json',
 'V/longest-callers-code-review-01.json','V/depth-first-caller-code-review-01.json',
 'V/simple-placement-caller-code-review-01.json','V/full-label-callers-code-review-01.json'):
 assert sum(r['path'].endswith(suffix)for r in record['reviewScopes'])==1,suffix
assert len(record['newCompleteCallers'])==7
for caller in record['newCompleteCallers']:
 binding=record['evidence'][caller['report']];assert binding['sha256']==caller['reportSha256']
 r=json.loads((root/binding['path']).read_bytes());assert r['passed']is True and r['comparison']['differences']==[]and r['violations']==[]
 assert r['rawStrict']['passed']is False and len(r['rawStrict']['differences'])==caller['rawGeneratedShapeHashDifferences']
 assert caller['projectedStrictDifferences']==0 and caller['extraCacheLayouts']==0
 assert r['recursiveEngineInvoked']and r['sameMetadataRegistryAndPools']and r['nativeWholeExecutions']==1
assert [c['rawGeneratedShapeHashDifferences']for c in record['newCompleteCallers']]==[4,6,6,5,4,4,5]
assert all(c['managerActuallySelected']is False for c in record['newCompleteCallers']if c['name']in('end-labels','center-labels'))
assert record['advancedLabels']['oldSixSelectorCasesReexecuted']is False
assert record['advancedLabels']['endPreCandidateExecutions']==1
assert record['phaseAlternatives']['rawCycleExceptionTextClassEquivalenceClaimed']is False
assert record['phaseAlternatives']['oldCyclesBoundedGuardsDeleted']is False
assert 'algorithms/layered/coffman_graham_general.py'not in tree
assert record['wholeAlgorithmsAccepted']==0
assert all(record[k]is False for k in('fullValidation','publicAPIIntegrated','installedPackageValidated','packagePublished'))
plan=json.loads((root/'docs/iteration-plan.json').read_bytes());assert plan['validationPolicy']['featureImplementationComplete']is False
active=plan['parallelPreparation']['progressRecord'].endswith('next-native-18.json')
if active:assert plan['parallelPreparation']['codeCheckpoint']==cp
print(json.dumps({'passed':True,'scope':'immutable191 source/evidence and limited named code/caller bindings only',
 'evidenceFiles':len(record['evidence']),'reviewScopes':len(record['reviewScopes']),'matchingSourceBindings':len(matched),
 'newCompleteCallers':7,'activePlanStillBatch18':active,'productsExecuted':0,'fullValidation':False}))
