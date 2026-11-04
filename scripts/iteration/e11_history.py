"""Freeze and purely recheck E09/E10 history without importing its product.

Only the original audit read closure is archived. No layout, old wheel, network
or full-project suite is executed. The immutable archive is separate from the
current package and the current history verifier.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
HISTORY='references/history/E09'
MANIFEST_SHA='4e5f6b3b56de907eed3680a1a47fb3cebc721d6191b2de9dc0afceca0bede625'
ARCHIVE_SHA='03f7463927723fc8ddb4fb77c73f0425aafdfc94ad44b0e69e3b3871e94eff3e'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):
    Path(path).write_bytes((json.dumps(value,indent=2,allow_nan=False)+'\n').encode())
def require(value,message):
    if not value:raise ValueError(message)


def original_checks(root,*,capture=False):
    """Import audit code only; forbid product imports and runtime subprocesses."""
    sys.dont_write_bytecode=True
    root=Path(root).resolve();reads=set()
    sys.path[:0]=[str(root/'scripts/iteration'),str(root/'scripts')]
    def audit(event,args):
        if event=='import' and (args[0]=='pyelk' or args[0].startswith('pyelk.')):
            raise ValueError('Archived product imports are forbidden')
        if event=='subprocess.Popen':raise ValueError('Historical checks cannot launch layout or external commands')
        if capture and event=='open' and isinstance(args[0],(str,bytes)):
            try:
                candidate=Path(args[0]).resolve()
                if candidate.is_file() and candidate.is_relative_to(root):
                    name=candidate.relative_to(root).as_posix()
                    if not name.startswith(('.git/','.local/','test-runs/')) and '__pycache__' not in candidate.parts:
                        reads.add(name)
            except (ValueError,OSError,TypeError):pass
    sys.addaudithook(audit)
    from validate_e09_runtime import check
    import e10,e10_benchmark,e10_instrument
    result=check(root);require(result.get('passed') is True,'Frozen E09 aggregate failed: '+str(result.get('errors')))
    matrix=e10.load(root/'references/e10-platform-matrix.json')
    cells=[e10.load(root/name) for name in matrix['cells']]
    require(e10.validate_matrix(cells,root)['passed'],'Frozen E10 wheel matrix failed')
    for name in ('windows-3.13-sdist.json','linux-3.14-sdist.json'):
        require(e10.validate_cell(e10.load(root/'references/e10'/name),root)['passed'],'Frozen E10 source-install representative failed: '+name)
    public=e10.load(root/'references/e10-benchmark.json')
    require(e10_benchmark.validate(public,root)['passed'],'Frozen E10 public benchmark failed')
    require(e10_instrument.validate(e10.load(root/'references/e10-instrumented.json'),public,root)['passed'],
            'Frozen E10 instrumented evidence failed')
    if capture:
        for module in tuple(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if filename:
                candidate=Path(filename).resolve()
                if candidate.is_relative_to(root) and candidate.suffix=='.py' and candidate.is_relative_to(root/'scripts'):
                    reads.add(candidate.relative_to(root).as_posix())
        # Retain the original runtime adapter universe, including files which
        # are read for hashing rather than imported by the pure validators.
        reads.update(p.relative_to(root).as_posix() for folder,pattern in
                     (('scripts','*.py'),('tools/reference','*.py'),('tools/reference','*.cjs'),('tools/platform','*.py'))
                     for p in (root/folder).glob(pattern))
        reads.update(p.relative_to(root).as_posix() for p in (root/'src/pyelk').rglob('*')
                     if p.is_file() and (p.suffix=='.py' or p.name=='py.typed' or '_licenses' in p.parts))
        reads.update(('README.md','pyproject.toml','UPSTREAM.json','docs/compatibility.json'))
        reads.discard('scripts/iteration/e11_history.py')
    return {'passed':True,'readFiles':sorted(reads),'historicalWheelCells':8,'historicalSourceRepresentatives':2,
            'historicalPublicSamples':18,'historicalInstrumentedCases':3,'historicalE09BehaviorItems':219,
            'runtimeReexecuted':False,'fullValidation':False}


def child_check(root,*,capture=False):
    args=[sys.executable,'-I',str(Path(__file__).resolve()),'--check-root',str(root)]
    if capture:args.append('--capture-closure')
    child=subprocess.run(args,capture_output=True,check=False)
    require(child.returncode==0,'Historical pure-check process failed: '+child.stderr.decode(errors='replace')+child.stdout.decode(errors='replace'))
    return json.loads(child.stdout)


def create(root=ROOT):
    root=Path(root).resolve();destination=root/HISTORY
    require(not destination.exists(),'Historical snapshot already exists; never overwrite original bytes')
    checked=child_check(root,capture=True)
    material={name:(root/name).read_bytes() for name in checked['readFiles']}
    installed=json.loads(material['references/e09-installed-check.json'])['installed']
    package=installed['packageFilesSha256']
    require(len(package)==43,'Expected original 43-file historical product')
    for name,fingerprint in package.items():
        require(digest(material['src/pyelk/'+name])==fingerprint,'Historical product differs from original installed wheel: '+name)
    wheel=root/'test-runs/20261103-E09-01/candidate-build-02/dist/py_elk-0.0.1a0-py3-none-any.whl'
    sdist=root/'test-runs/20261103-E09-01/candidate-build-02/dist/py_elk-0.0.1a0.tar.gz'
    # The E10 artifact record retains the exact source archive location.
    if not sdist.is_file():
        cell=json.loads(material['references/e10/windows-3.13-sdist.json'])
        sdist=Path(cell['installation']['artifact'])
    require(digest(wheel.read_bytes())==installed['wheelSha256'],'Original historical wheel is missing or changed')
    require(digest(sdist.read_bytes())=='6fe04b1725955673d46b1e8dbdca3dc94cd81308b5276038e2ab2e2a4e1bd3ce',
            'Original historical source archive differs')
    destination.mkdir(parents=True)
    archive=destination/'audit-material.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as target:
        for name,raw in sorted(material.items()):target.writestr(name,raw)
    (destination/wheel.name).write_bytes(wheel.read_bytes())
    (destination/sdist.name).write_bytes(sdist.read_bytes())
    manifest={'schema':'py-elk-e09-e10-historical-audit-material/v1','iterations':['E09','E10'],
              'archiveSha256':digest(archive.read_bytes()),'filesSha256':{n:digest(v) for n,v in sorted(material.items())},
              'wheel':wheel.name,'wheelSha256':digest(wheel.read_bytes()),'sdist':sdist.name,'sdistSha256':digest(sdist.read_bytes()),
              'productFilesSha256':package,'originalProductFileCount':43,'originalVersion':installed['version'],
              'originalEvidence':{name:digest(raw) for name,raw in material.items() if name in
                 ('references/e09-installed-check.json','references/e09-coverage-installed.json',
                  'references/e09-runtime-audit.json','references/e10-platform-matrix.json',
                  'references/e10-benchmark.json','references/e10-instrumented.json')},
              'runtimeReexecuted':False,'fullValidation':False,'historicalExecutionAuthenticated':False,
              'limitation':'Original immutable product, declarations, source approvals, raw receipts and pure audit closure; no archived package execution or certification of the current package.'}
    save(destination/'manifest.json',manifest)
    return {'created':True,'archiveSha256':manifest['archiveSha256'],'manifestSha256':digest((destination/'manifest.json').read_bytes()),
            'fileCount':len(material),'rawBytes':sum(map(len,material.values())),'archiveBytes':archive.stat().st_size,
            'pureChecks':{k:v for k,v in checked.items() if k!='readFiles'}}


def material(root=ROOT):
    folder=Path(root)/HISTORY;manifest_raw=(folder/'manifest.json').read_bytes()
    require(digest(manifest_raw)==MANIFEST_SHA,'Historical manifest bytes differ')
    manifest=json.loads(manifest_raw);raw=(folder/'audit-material.zip').read_bytes()
    require(digest(raw)==manifest['archiveSha256']==ARCHIVE_SHA,'Historical archive bytes differ')
    for kind in ('wheel','sdist'):
        require(digest((folder/manifest[kind]).read_bytes())==manifest[kind+'Sha256'],'Historical '+kind+' bytes differ')
    files={}
    with zipfile.ZipFile(folder/'audit-material.zip') as archive:
        names=archive.namelist();require(len(names)==len(set(names)) and set(names)==set(manifest['filesSha256']),
                                        'Historical input denominator differs')
        for name in names:
            path=PurePosixPath(name)
            require(not path.is_absolute() and '\\' not in name and ':' not in name and all(p not in ('','.','..') for p in name.split('/')),
                    'Historical archive path escapes extraction root')
            raw=archive.read(name);require(digest(raw)==manifest['filesSha256'][name],'Historical input bytes differ: '+name)
            files[name]=raw
    require(manifest['originalProductFileCount']==len(manifest['productFilesSha256'])==43,'Historical product denominator differs')
    return files


def check(root=ROOT):
    try:
        files=material(root)
        with tempfile.TemporaryDirectory(prefix='pyelk-e09-e10-history-') as folder:
            frozen=Path(folder)
            for name,raw in files.items():
                target=frozen/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            evidence=child_check(frozen)
        return {'passed':True,'errors':[],'status':'E09_E10_HISTORICAL_EVIDENCE_VALIDATED',
                'historicalPackageBytesValidated':True,'currentPackageBytesValidated':False,
                'runtimeReexecuted':False,'fullValidation':False,'historicalExecutionAuthenticated':False,
                'originalChecks':evidence}
    except (ValueError,KeyError,TypeError,OSError,zipfile.BadZipFile) as error:
        return {'passed':False,'errors':[str(error)],'currentPackageBytesValidated':False,'runtimeReexecuted':False,'fullValidation':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--create',action='store_true')
    parser.add_argument('--check-root',type=Path);parser.add_argument('--capture-closure',action='store_true')
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--out',type=Path);args=parser.parse_args()
    if args.check_root:result=original_checks(args.check_root,capture=args.capture_closure)
    elif args.create:result=create(args.root)
    else:result=check(args.root)
    if args.out:save(args.out,result)
    print(json.dumps(result));return 0 if result.get('passed',result.get('created',False)) else 1


if __name__=='__main__':raise SystemExit(main())
