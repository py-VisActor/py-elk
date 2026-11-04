import json,hashlib,subprocess
from pathlib import Path
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=Path('docs/changes/20261104-next-native-04.json');d=json.loads(p.read_bytes());cp=Path(d['checkpoint']['path']);assert sha(cp)==d['checkpoint']['sha256'];m=json.loads(cp.read_bytes());assert m['sourceFiles']==71 and len(m['sourceTreeSha256'])==71
for e in d['evidence'].values():assert sha(Path(e['path']))==e['sha256']
checks=[('references/next-native-evidence/04/presence-code-review.json',['options/schema.py','options/element.py','execution/node_micro.py']),('references/next-native-evidence/04/geometry-code-review.json',['execution/json_transfer.py']),('references/next-native-evidence/04/ns-code-review.json',['algorithms/layered/north_south_ports.py','algorithms/layered/import_export.py'])]
for file,names in checks:
 review=json.loads(Path(file).read_bytes());assert review['accepted'] and not review['blockers']
 for name in names:assert m['sourceTreeSha256'][name] in review['filesSha256'].values(),name
plan=json.loads(Path('docs/iteration-plan.json').read_bytes());assert plan['parallelPreparation']['codeCheckpoint']['sha256']==d['checkpoint']['sha256'];assert plan['parallelPreparation']['wholeAlgorithmsAccepted']==0;assert plan['validationPolicy']['featureImplementationComplete'] is False
rows=[]
for name in ['references/e18-force-stress-sources.json','references/next-numeric-import-sources.json']:
 raw=Path(name).read_bytes();process=subprocess.Popen(['git','hash-object','--stdin','--path',name],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);stdout,stderr=process.communicate(raw);expected=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert process.returncode==0 and stdout.decode().strip()==expected,(name,stderr);rows.append(dict(path=name,pid=process.pid,exitCode=process.returncode,rawBlobSha1=expected,actualGitBlobSha1=stdout.decode().strip(),stderr=stderr.decode()))
print(json.dumps(dict(passed=True,portableEvidenceBindingsChecked=len(d['evidence']),checkpointSourceFiles=m['sourceFiles'],changedBytePolicyChecks=rows,sourceCodeReexecuted=False,fullValidation=False)))
