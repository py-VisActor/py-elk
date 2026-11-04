import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
progress_path=ROOT/'docs/changes/20261104-next-native-08.json';record=json.loads(progress_path.read_text('utf-8'))
for item in record['evidence'].values():assert sha(ROOT/item['path'])==item['sha256'],item['path']
cp=record['checkpoint'];assert sha(ROOT/cp['path'])==cp['sha256']
m=json.loads((ROOT/cp['path']).read_text('utf-8'));tree=m['sourceTreeSha256'];assert len(tree)==m['sourceFiles']==96
assert sha(ROOT/m['baseArchive'])==m['baseArchiveSha256']
for name,item in m['overrides'].items():
    obj=ROOT/'migration/next-native/objects'/(item['sha256']+'.bin')
    assert sha(obj)==tree[name]==item['sha256'],name
reviews=('runtime-properties-code-review-01','object-properties-code-review-01','property-snapshot-code-review-01',
         'basic-crossings-code-review-01','ns-crossings-code-review-01','hyperedge-crossings-code-review-01',
         'disco-polygon-code-review-01','polyomino-grid-foundation-code-review-01',
         'polyomino-raster-code-review-01','rectpacking-drawing-row-code-review-01')
matched={}
for review_name in reviews:
    entry=record['evidence']['test-runs/20261104-HOST-08/V/'+review_name+'.json']
    review=json.loads((ROOT/entry['path']).read_text('utf-8'));assert review['accepted']is True and not review['blockers']
    for path,value in review['filesSha256'].items():
        path=path.replace('\\','/')
        if '/src/pyelk/'not in path:continue
        name=path.split('/src/pyelk/',1)[1]
        if tree.get(name)==value:matched[name]={'sha256':value,'review':review_name,'scope':review.get('scope')}
required=['options/generic.py','options/schema.py','options/element.py','options/resolution.py',
          'options/_generic_data.py','options/_core_defaults.py','options/_object_data.py',
          'execution/json_transfer.py','execution/node_micro.py','execution/properties.py',
          'algorithms/layered/crossing_counter.py','algorithms/layered/hyperedge_crossings.py',
          'algorithms/disco.py','algorithms/polyomino.py','algorithms/rectpacking.py']
assert all(name in matched for name in required),[name for name in required if name not in matched]
plan=json.loads((ROOT/'docs/iteration-plan.json').read_text('utf-8'))
assert plan['validationPolicy']['featureImplementationComplete']is False
assert plan['parallelPreparation']['progressRecord'].endswith('next-native-08.json')
assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==0
assert all(item['status']=='planned'for item in plan['iterations']if item['id']in record['officialIterationsRemainPlanned'])
assert record['propertyRegistry']['declarations']==243 and record['propertyRegistry']['rawConstructibleProperties']==235
assert record['propertyRegistry']['sourceUnavailableRawFactories']==8
print(json.dumps({'passed':True,'scope':'source-only fixed96/archive bindings; matched reviews retain their declared subsets',
                  'evidenceFiles':len(record['evidence']),'matchedSourceReviewBindings':matched,
                  'checkpointFiles':len(tree),'productExecuted':False,'fullValidation':False,'wholeAlgorithmsAccepted':0}))
