"""Byte-preserving offline option-evidence archive; never executes a layout.

Inspect before packing:
  python scripts/iteration/option_evidence.py --inventory
Build or incrementally rebuild after updating the ledger:
  python scripts/iteration/option_evidence.py --build [--replace]
On a clean checkout (the exact checker dependencies must already be present):
  python scripts/iteration/option_evidence.py --restore
  python scripts/iteration/option_coverage.py --check --evidence-manifest references/full-native-closure/options.manifest.json

The archive contains the ledger's actual JSON inputs, not source snapshots.
Raw absolute paths inside observations remain untouched. Only explicit input
paths are resolved. --root-map ORIGINAL=CURRENT on option_coverage supplies an
explicit old Windows root mapping when such an input path is used; no fallback
to the original machine/workspace is permitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import os
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST=Path('references/full-native-closure/options.manifest.json')
DEFAULT_ARCHIVE=Path('references/full-native-closure/options.zip')
CODE_DEPENDENCIES=(
    'scripts/iteration/option_evidence.py','scripts/iteration/option_coverage.py',
    'scripts/validate_full_layered.py','scripts/iteration/check_layered_saved.py',
    'scripts/layout_checks.py','scripts/source_read_cache.py')


def digest(raw):return hashlib.sha256(raw).hexdigest()


def safe_path(root,name):
    """Accept portable, canonical repository-relative names only."""
    if type(name)is not str or not name or '\\'in name or ':'in name:
        raise ValueError('Invalid evidence member name: '+repr(name))
    path=PurePosixPath(name)
    if path.is_absolute()or any(p in ('','.','..')for p in name.split('/'))or str(path)!=name:
        raise ValueError('Escaping or noncanonical evidence member: '+name)
    root=Path(root).resolve();target=(root/Path(*path.parts)).resolve()
    if not target.is_relative_to(root):raise ValueError('Evidence escapes destination: '+name)
    return target


def read(path):return json.loads(Path(path).read_text('utf8'))


def inventory(root=ROOT,original_root=None):
    root=Path(root).resolve();ledger_path=root/'docs/option-coverage.json';ledger=read(ledger_path)
    original_root=str(root)if original_root is None else original_root
    expected={}
    def add(name,sha=None):
        if PureWindowsPath(name).is_absolute():
            try:name=PureWindowsPath(name).relative_to(PureWindowsPath(original_root)).as_posix()
            except ValueError:raise ValueError('Unmapped original evidence root: '+name)from None
        target=safe_path(root,name)
        raw=target.read_bytes();actual=digest(raw)
        if sha is not None and actual!=sha:raise ValueError('Referenced SHA mismatch: '+name)
        if name in expected and expected[name]['sha256']!=actual:raise ValueError('Conflicting binding: '+name)
        expected[name]={'path':name,'sha256':actual,'bytes':len(raw),
                        'storage':'archive'if target.suffix=='.json'else'repository',
                        'estimatedDeflateBytes':len(zlib.compress(raw,9))}
    add('docs/option-coverage.json')
    for item in ledger['evidence'].values():add(item['path'],item['sha256'])
    for case in ledger['caseIndex'].values():add(case['request'],case['requestSha256'])
    for report_path in ledger.get('effectReports',[]):
        add(report_path)
        for row in read(safe_path(root,report_path))['rows']:
            for key in ('request','reference','native'):
                item=row[key];add(item['path'],item['sha256'])
    for name in CODE_DEPENDENCIES:add(name)
    rows=sorted(expected.values(),key=lambda r:r['path'])
    return {'schema':'pyelk-option-evidence-manifest/v1',
            'ledgerSha256':digest(ledger_path.read_bytes()),'originalExecutionRoot':original_root,
            'pathPolicy':'Repository-relative members; explicit original-root mapping only; raw JSON is unchanged.',
            'files':rows,'fileCount':len(rows),
            'archiveFileCount':sum(r['storage']=='archive'for r in rows),
            'repositoryDependencyCount':sum(r['storage']=='repository'for r in rows),
            'uncompressedBytes':sum(r['bytes']for r in rows if r['storage']=='archive'),
            'estimatedDeflateBytes':sum(r['estimatedDeflateBytes']for r in rows if r['storage']=='archive'),
            'productsExecuted':0,'referenceProcessesExecuted':0}


def validate_manifest(manifest,root):
    if manifest.get('schema')!='pyelk-option-evidence-manifest/v1':raise ValueError('Unknown evidence manifest')
    names=set()
    for row in manifest['files']:
        name=row['path'];safe_path(root,name)
        if name in names:raise ValueError('Duplicate evidence member: '+name)
        names.add(name)
        if row['storage']not in ('archive','repository'):raise ValueError('Unknown storage kind')
        if type(row['bytes'])is not int or row['bytes']<0:raise ValueError('Invalid evidence size')
        if type(row['sha256'])is not str or len(row['sha256'])!=64 or any(c not in '0123456789abcdef'for c in row['sha256']):
            raise ValueError('Invalid evidence digest')
    if manifest['fileCount']!=len(names):raise ValueError('Evidence denominator differs')
    ledger=next(r for r in manifest['files']if r['path']=='docs/option-coverage.json')
    if ledger['sha256']!=manifest['ledgerSha256']:raise ValueError('Ledger binding differs')


def check_bytes(raw,row):
    if len(raw)!=row['bytes']or digest(raw)!=row['sha256']:
        raise ValueError('Evidence bytes/SHA differ: '+row['path'])


def verify_restored(manifest_path,root=ROOT):
    manifest=read(manifest_path);validate_manifest(manifest,root)
    for row in manifest['files']:check_bytes(safe_path(root,row['path']).read_bytes(),row)
    return {'passed':True,'verifiedFiles':len(manifest['files']),
            'manifestSha256':digest(Path(manifest_path).read_bytes()),
            'productsExecuted':0,'referenceProcessesExecuted':0}


def build_archive(manifest_path,archive_path,root=ROOT,replace=False,original_root=None):
    manifest=inventory(root,original_root)
    if not replace and (manifest_path.exists()or archive_path.exists()):raise FileExistsError('Use --replace to rebuild the evidence archive')
    archive_path.parent.mkdir(parents=True,exist_ok=True);manifest_path.parent.mkdir(parents=True,exist_ok=True)
    temporary=archive_path.with_name(archive_path.name+'.new')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as stream:
        for row in manifest['files']:
            if row['storage']!='archive':continue
            raw=safe_path(root,row['path']).read_bytes();check_bytes(raw,row)
            info=zipfile.ZipInfo(row['path'],date_time=(2026,11,4,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            stream.writestr(info,raw,compresslevel=9)
    manifest['archive']={'path':archive_path.resolve().relative_to(Path(root).resolve()).as_posix(),
                         'bytes':temporary.stat().st_size,'sha256':digest(temporary.read_bytes())}
    os.replace(temporary,archive_path)
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    return manifest


def restore(manifest_path,archive_path,destination):
    manifest=read(manifest_path);destination=Path(destination).resolve();validate_manifest(manifest,destination)
    raw=archive_path.read_bytes()
    if digest(raw)!=manifest['archive']['sha256']or len(raw)!=manifest['archive']['bytes']:raise ValueError('Archive SHA/size differs')
    expected={r['path']:r for r in manifest['files']if r['storage']=='archive'}
    pending=[]
    # Validate all members and repository dependencies before writing anything.
    for row in manifest['files']:
        target=safe_path(destination,row['path'])
        if row['storage']=='repository' or target.exists():check_bytes(target.read_bytes(),row)
    with zipfile.ZipFile(archive_path)as stream:
        infos=stream.infolist()
        if len(infos)!=len(expected)or {i.filename for i in infos}!=set(expected):raise ValueError('Archive members differ from manifest')
        for info in infos:
            target=safe_path(destination,info.filename);row=expected[info.filename]
            if info.file_size!=row['bytes']or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Invalid archive member size/type')
            value=stream.read(info);check_bytes(value,row)
            if not target.exists():pending.append((target,value))
    for path,value in pending:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb')as stream:stream.write(value)
    report=verify_restored(manifest_path,destination);report['restoredFiles']=len(pending)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    mode=parser.add_mutually_exclusive_group(required=True)
    for name in ('inventory','build','restore','verify'):mode.add_argument('--'+name,action='store_true')
    parser.add_argument('--manifest',type=Path,default=ROOT/DEFAULT_MANIFEST)
    parser.add_argument('--archive',type=Path,default=ROOT/DEFAULT_ARCHIVE)
    parser.add_argument('--destination',type=Path,default=ROOT)
    parser.add_argument('--original-root',help='Explicit original Windows root when rebuilding from a relocated checkout')
    parser.add_argument('--replace',action='store_true');parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.inventory:report=inventory(original_root=args.original_root)
    elif args.build:report=build_archive(args.manifest,args.archive,replace=args.replace,original_root=args.original_root)
    elif args.restore:report=restore(args.manifest,args.archive,args.destination)
    else:report=verify_restored(args.manifest,args.destination)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x',encoding='utf8')as stream:json.dump(report,stream,indent=2)
    print(json.dumps({key:value for key,value in report.items()if key!='files'},ensure_ascii=False))


if __name__=='__main__':main()
