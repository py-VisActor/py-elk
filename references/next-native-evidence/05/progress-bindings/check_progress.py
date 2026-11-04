import json,hashlib
from pathlib import Path
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('docs/changes/20261104-next-native-05.json');d=json.loads(p.read_bytes());cp=Path(d['checkpoint']['path']);assert sha(cp)==d['checkpoint']['sha256'];m=json.loads(cp.read_bytes());assert m['sourceFiles']==74 and len(m['sourceTreeSha256'])==74
for e in d['evidence'].values():assert sha(Path(e['path']))==e['sha256']
for filename,names in [('e18-force-stress-code-review-01.json',['algorithms/force.py','algorithms/stress.py']),('e18-stress-inline-default-review-01.json',['options/schema.py']),('p07-code-review.json',['algorithms/layered/inverted_ports.py','algorithms/layered/hyperedge_merger.py'])]:
 r=json.loads((Path('references/next-native-evidence/05')/filename).read_bytes());assert r['accepted'] and not r['blockers']
 for name in names:assert m['sourceTreeSha256'][name] in r['filesSha256'].values(),name
plan=json.loads(Path('docs/iteration-plan.json').read_bytes());assert plan['parallelPreparation']['codeCheckpoint']['sha256']==d['checkpoint']['sha256'];assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==0;assert plan['validationPolicy']['featureImplementationComplete'] is False
assert d['forceStress']['newOriginalCases']==5 and d['portDummyKernels']['newOriginalLocalObjectCases']==3
assert d['forceStress']['generatedRuntimeHashDifferencesRetained']==20
print(json.dumps({'passed':True,'portableEvidenceBindingsChecked':len(d['evidence']),'checkpointSourceFiles':74,'sourceCodeOrOriginalReexecuted':False,'fullValidation':False}))
