"""Save/restore isolated migration source checkpoints outside the release src.

Only source bytes are copied. This tool performs no layout and certifies no
algorithm, candidate, or historical execution. Existing destinations are kept.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path,PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[2]
STAGE='migration/next-native'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def safe(name):
    p=PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or any(x in ('','..','.') for x in name.split('/')):
        raise ValueError('Unsafe source member '+name)
    return p
def files(folder):
    return {p.relative_to(folder).as_posix():p.read_bytes() for p in Path(folder).rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def keep_object(stage,raw):
    folder=stage/'objects';folder.mkdir(exist_ok=True)
    target=folder/(digest(raw)+'.bin')
    if target.exists():
        if target.read_bytes()!=raw:raise ValueError('Content-addressed source object changed')
    else:
        with target.open('xb') as out:out.write(raw)


def snapshot(root=ROOT,workspace=None):
    root=Path(root);workspace=Path(workspace or root/'.local/migration-next')
    base=load(workspace/'base.json')['baseFilesSha256'];stage=root/STAGE
    stage.mkdir(parents=True,exist_ok=True);archive=stage/'base-sources.zip'
    if not archive.exists():
        raw={name:(root/'src/pyelk'/safe(name)).read_bytes() for name in base}
        if any(digest(raw[name])!=expected for name,expected in base.items()):
            raise ValueError('Original release source changed before baseline was preserved')
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as out:
            for name in sorted(raw):out.writestr(name,raw[name])
    if (stage/'manifest.json').exists():
        previous_raw=(stage/'manifest.json').read_bytes();previous=json.loads(previous_raw)
        if digest(archive.read_bytes())!=previous['baseArchiveSha256'] or base!=previous['baseFilesSha256']:
            raise ValueError('Immutable source baseline changed')
        history=stage/'checkpoints';history.mkdir(exist_ok=True)
        saved=history/(digest(previous_raw)+'.json')
        if not saved.exists():
            with saved.open('xb') as out:out.write(previous_raw)
        for name,entry in previous['overrides'].items():
            old=(root/safe(entry['path'])).read_bytes()
            if digest(old)!=entry['sha256']:raise ValueError('Previous source override changed before checkpoint')
            keep_object(stage,old)
    current=files(workspace/'src/pyelk');overrides={}
    for name,raw in sorted(current.items()):
        safe(name)
        if digest(raw)!=base.get(name):
            keep_object(stage,raw)
            p=stage/'overrides'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            overrides[name]={'path':p.relative_to(root).as_posix(),'sha256':digest(raw)}
    if {n:digest(v) for n,v in files(workspace/'src/pyelk').items()}!={n:digest(v) for n,v in current.items()}:
        raise ValueError('Private source changed during checkpoint; rerun after owner freeze')
    result={'schema':'py-elk-next-source-checkpoint/v1','baseArchive':archive.relative_to(root).as_posix(),
            'baseArchiveSha256':digest(archive.read_bytes()),'baseFilesSha256':base,'overrides':overrides,
            'removed':sorted(set(base)-set(current)),'sourceFiles':len(current),
            'sourceTreeSha256':{n:digest(v) for n,v in current.items()},
            'fullValidation':False,'algorithmAccepted':False,'publicAPIIntegrated':False,'packagePublished':False}
    current_raw=(json.dumps(result,indent=2)+'\n').encode('utf8')
    # A newly returned snapshot must already have an immutable path, without
    # requiring a later snapshot to archive the current manifest first.
    history=stage/'checkpoints';history.mkdir(exist_ok=True)
    saved=history/(digest(current_raw)+'.json')
    if saved.exists():
        if saved.read_bytes()!=current_raw:raise ValueError('Immutable current checkpoint changed')
    else:
        with saved.open('xb') as out:out.write(current_raw)
    (stage/'manifest.json').write_bytes(current_raw)
    return result


def restore(destination,root=ROOT,manifest_path=None):
    root=Path(root);manifest=load(manifest_path or root/STAGE/'manifest.json');archive=root/safe(manifest['baseArchive'])
    if digest(archive.read_bytes())!=manifest['baseArchiveSha256']:raise ValueError('Base source archive changed')
    with zipfile.ZipFile(archive) as source:
        names=source.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(manifest['baseFilesSha256']):raise ValueError('Base file denominator changed')
        content={name:source.read(str(safe(name))) for name in names}
    if any(digest(raw)!=manifest['baseFilesSha256'][name] for name,raw in content.items()):
        raise ValueError('Base source file bytes differ')
    for name in manifest['removed']:content.pop(str(safe(name)))
    for name,entry in manifest['overrides'].items():
        safe(name)
        if not re.fullmatch('[0-9a-f]{64}',entry['sha256']):raise ValueError('Invalid source object digest')
        source=root/safe(entry['path']);raw=source.read_bytes() if source.is_file() else b''
        if digest(raw)!=entry['sha256']:
            raw=(root/STAGE/'objects'/(entry['sha256']+'.bin')).read_bytes()
        if digest(raw)!=entry['sha256']:raise ValueError('Checkpoint source override changed: '+name)
        content[name]=raw
    if {n:digest(v) for n,v in content.items()}!=manifest['sourceTreeSha256']:raise ValueError('Restored source tree differs')
    destination=Path(destination)
    if destination.exists():raise FileExistsError('Keep existing migration workspace: '+str(destination))
    destination.mkdir(parents=True)
    for name,raw in content.items():
        target=destination/'src/pyelk'/safe(name);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write(raw)
    (destination/'base.json').write_text(json.dumps({'baseFilesSha256':manifest['baseFilesSha256']},indent=2)+'\n',encoding='utf8')
    return {'sourceFiles':len(content),'fullValidation':False,'algorithmAccepted':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='action',required=True)
    commands.add_parser('snapshot').add_argument('--workspace',type=Path)
    restore_parser=commands.add_parser('restore');restore_parser.add_argument('--destination',required=True,type=Path)
    restore_parser.add_argument('--manifest',type=Path,help='Optional immutable earlier source checkpoint')
    args=parser.parse_args();result=snapshot(workspace=args.workspace) if args.action=='snapshot' else restore(args.destination,manifest_path=args.manifest)
    response={'sourceFiles':result['sourceFiles'],'fullValidation':False,'algorithmAccepted':False}
    if args.action=='snapshot':
        raw=(ROOT/STAGE/'manifest.json').read_bytes();response['checkpointPath']=str(Path(STAGE)/'checkpoints'/(digest(raw)+'.json'))
        response['checkpointSha256']=digest(raw)
    print(json.dumps(response))


if __name__=='__main__':main()
