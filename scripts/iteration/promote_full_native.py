"""Promote a frozen implementation tree, retaining every prior source byte.

This copies code only. It neither executes layout nor certifies correctness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from next_workspace import ROOT,files,snapshot


def hashes(values):
    return {name:hashlib.sha256(raw).hexdigest()for name,raw in sorted(values.items())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,default=ROOT/'.local/migration-next')
    parser.add_argument('--backup',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    for target in(args.backup,args.report):
        if target.exists():parser.error('Refusing to overwrite '+str(target))
    source=args.workspace/'src/pyelk';destination=ROOT/'src/pyelk'
    before=files(destination);current=files(source)
    if not current or not set(before)<=set(current):
        parser.error('Promotion must contain every existing source member')
    checkpoint=snapshot(workspace=args.workspace)
    if hashes(files(source))!=hashes(current):raise ValueError('Source changed before promotion')
    args.backup.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.backup,'x',compression=zipfile.ZIP_DEFLATED)as archive:
        for name,raw in sorted(before.items()):archive.writestr(name,raw)
    with zipfile.ZipFile(args.backup)as archive:
        if {name:archive.read(name)for name in archive.namelist()}!=before:
            raise ValueError('Backup bytes differ')
    for name,raw in sorted(current.items()):
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
    after=files(destination)
    if hashes(after)!=hashes(current):raise ValueError('Promoted source bytes differ')
    manifest_raw=(ROOT/'migration/next-native/manifest.json').read_bytes()
    report={'schema':'py-elk-full-native-promotion/v1','promoted':True,
            'previousSourceFilesSha256':hashes(before),'sourceFilesSha256':hashes(after),
            'previousSourceFileCount':len(before),'sourceFileCount':len(after),
            'pythonModuleCount':sum(name.endswith('.py')for name in after),
            'backup':str(args.backup),'backupSha256':hashlib.sha256(args.backup.read_bytes()).hexdigest(),
            'checkpointSha256':hashlib.sha256(manifest_raw).hexdigest(),
            'checkpointSourceFiles':checkpoint['sourceFiles'],
            'layoutExecutions':0,'correctnessVerified':False,'packagePublished':False}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key]for key in('promoted','previousSourceFileCount',
          'sourceFileCount','pythonModuleCount','checkpointSha256','correctnessVerified')}))


if __name__=='__main__':main()
