import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

p = ROOT / 'docs/changes/20261104-next-native-06.json'
record = json.loads(p.read_text('utf-8'))
for item in record['evidence'].values():
    assert sha(ROOT / item['path']) == item['sha256'], item['path']
cp = record['checkpoint']
assert sha(ROOT / cp['path']) == cp['sha256']
m = json.loads((ROOT / cp['path']).read_text('utf-8'))
assert m['sourceFiles'] == 87
files = dict(m['baseFilesSha256'])
for name in m['removed']:
    files.pop(name, None)
for name, item in m['overrides'].items():
    files[name] = item['sha256']
assert len(files) == 87
expected = {
    'execution/node_micro.py': 'b18bd4caf1f8fa097730ab4effc6a5973adeeebaf9c0a996e95206609ad61ff3',
    'execution/json_transfer.py': '4dc872245bea073d3c8f4697d3a98eff22982a16b5df4b0dbd7371f0789bc39c',
    'execution/providers.py': '5e746d76efb4c8ed6a19a335b4a579f432549fc3ed3b0f588ed581e2825be91e',
    'algorithms/fixed.py': 'e9025290ecb18f1460adc9a8c49499ad9b66b576b213eeb4c2b68a565ae80653',
    'algorithms/spore.py': '7ae8355944accd67d0aa02ac02b9b7a3c83fe0aba5126d7efed14750169d7b96',
}
for name, value in expected.items():
    assert files[name] == value, name
plan = json.loads((ROOT / 'docs/iteration-plan.json').read_text('utf-8'))
assert plan['validationPolicy']['featureImplementationComplete'] is False
assert plan['parallelPreparation']['wholeAlgorithmsAccepted'] == 0
assert plan['parallelPreparation']['progressRecord'].endswith('next-native-06.json')
assert all(i['status'] == 'planned' for i in plan['iterations'] if i['id'] in record['officialIterationsRemainPlanned'])
assert record['privateSchemas'] == 63 and record['publicMainSchemasUnchanged'] == 9
print(json.dumps({'passed': True, 'scope': 'source-only archived bindings, no product execution',
                  'evidenceFiles': len(record['evidence']), 'checkpointFiles': len(files),
                  'fullValidation': False, 'wholeAlgorithmsAccepted': 0}))
