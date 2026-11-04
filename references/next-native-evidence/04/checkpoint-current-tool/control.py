import json,tempfile,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path('scripts/iteration').resolve()))
import next_workspace as n
sha=lambda b:hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory(prefix='py-elk-current-checkpoint-') as temp:
 root=Path(temp);source=root/'src/pyelk';source.mkdir(parents=True);original=b'original\r\n';(source/'sample.py').write_bytes(original)
 ws=root/'work';(ws/'src/pyelk').mkdir(parents=True);(ws/'src/pyelk/sample.py').write_bytes(b'first\r\n');(ws/'base.json').write_text(json.dumps({'baseFilesSha256':{'sample.py':sha(original)}}))
 n.snapshot(root=root,workspace=ws);raw=(root/n.STAGE/'manifest.json').read_bytes();first=root/n.STAGE/'checkpoints'/(sha(raw)+'.json');assert first.read_bytes()==raw
 n.restore(root/'first-restored',root=root,manifest_path=first);assert (root/'first-restored/src/pyelk/sample.py').read_bytes()==b'first\r\n'
 (ws/'src/pyelk/sample.py').write_bytes(b'second\n');n.snapshot(root=root,workspace=ws)
 n.restore(root/'old-after-change',root=root,manifest_path=first);assert (root/'old-after-change/src/pyelk/sample.py').read_bytes()==b'first\r\n'
 assert first.read_bytes()==raw
print(json.dumps({'passed':True,'currentCheckpointImmediatelyRestorable':True,'previousCheckpointRestorableAfterMutation':True,'actualProjectManifestChanged':False,'helperSha256':sha(Path(n.__file__).read_bytes()),'fullValidation':False}))
