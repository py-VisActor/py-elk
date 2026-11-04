"""E11 source/license and same-candidate archive checks, without importing pyelk.

The source-only CI rule covers metadata and license changes. Any mathematical
AST change or new runtime module is rejected and needs a new affected-check plan.
"""
from __future__ import annotations
import argparse
import ast
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import tomllib
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BASE='references/history/E09/py_elk-0.0.1a0-py3-none-any.whl'
BASE_SHA='739f04ebce2782894023dd58b3f1e2e35efda8717f8bdd956c3f7967acedc593'
APACHE_SHA='cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30'
ADDED={'_licenses/Apache-2.0.txt','_licenses/NOTICE-GWT-Random.md'}


def digest(raw):return hashlib.sha256(raw).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)


def source_ast(raw, name):
    tree=ast.parse(raw)
    if name=='__init__.py':
        matches=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and
                 isinstance(n.targets[0],ast.Name) and n.targets[0].id=='__version__']
        require(len(matches)==1 and isinstance(matches[0].value,ast.Constant) and
                type(matches[0].value.value) is str,'Expected one literal package version')
        matches[0].value=ast.Constant(value='<release-version-only>')
    return ast.dump(tree,include_attributes=False)


def runtime_unchanged(root=ROOT):
    root=Path(root);raw=(root/BASE).read_bytes()
    require(digest(raw)==BASE_SHA,'Historical source baseline wheel bytes differ')
    with zipfile.ZipFile(root/BASE) as archive:
        old={n[len('pyelk/'):]:archive.read(n) for n in archive.namelist() if n.startswith('pyelk/') and not n.endswith('/')}
    python={n for n in old if n.endswith('.py')}
    current={p.relative_to(root/'src/pyelk').as_posix() for p in (root/'src/pyelk').rglob('*.py')}
    require(current==python and len(python)==35,'Runtime module additions/removals need a new affected-check plan')
    ast_hashes={}
    for name in sorted(python):
        before=source_ast(old[name],name);after=source_ast((root/'src/pyelk'/name).read_bytes(),name)
        require(before==after,'Runtime AST changed; E11 metadata/license check cannot certify implementation: '+name)
        ast_hashes[name]=digest(after.encode())
    for name in old.keys()-python:
        require((root/'src/pyelk'/name).read_bytes()==old[name],'Previously shipped license/type bytes changed: '+name)
    return old,ast_hashes


def check_source(root=ROOT, *, require_stable=True):
    root=Path(root)
    try:
        old,ast_hashes=runtime_unchanged(root)
        project=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf8'))
        metadata=project['project'];version=metadata['version']
        require(metadata['name']=='py-elk' and type(version) is str and bool(version) and
                (not require_stable or re.fullmatch(r'\d+\.\d+\.\d+',version)),
                'Formal candidate needs a stable project version')
        version_nodes=[n for n in ast.parse((root/'src/pyelk/__init__.py').read_bytes()).body
                       if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets)]
        require(len(version_nodes)==1 and version_nodes[0].value.value==version,'Imported/project versions differ')
        require(metadata.get('dependencies',[])==[] and metadata['requires-python']=='>=3.11',
                'Unexpected runtime dependency or Python requirement')
        expression=metadata.get('license')
        decision=json.loads((root/'docs/decisions/0009-project-license.json').read_bytes())
        require(decision['status']=='selected' and decision['projectLicenseSelected'] is True,
                'Project license choice remains pending; a proposal is not a selection')
        require(type(expression) is str and expression==decision['distributionExpression'],
                'Mixed-source SPDX expression differs from the selected project decision')
        require((root/'LICENSE').is_file() and (root/'LICENSE').stat().st_size>100,
                'Project LICENSE is required before candidate acceptance')
        require(digest((root/'LICENSE').read_bytes())==decision['projectLicenseTextSha256'],
                'Project LICENSE differs from the selected license text')
        require(metadata.get('urls',{}).get('Repository')=='https://github.com/py-VisActor/py-elk',
                'Published source repository URL is missing or differs')
        patterns=metadata.get('license-files',[])
        expected_patterns={'LICENSE','THIRD_PARTY_NOTICES.md','src/pyelk/_licenses/*.md','src/pyelk/_licenses/*.txt'}
        require(set(patterns)==expected_patterns and len(patterns)==len(expected_patterns),'Explicit source license files are incomplete')
        data=project['tool']['setuptools']['package-data']['pyelk']
        require(set(data)=={'py.typed','_licenses/*.md','_licenses/*.txt'} and len(data)==3,
                'Package data must include Apache text and all original notices')
        apache=(root/'src/pyelk/_licenses/Apache-2.0.txt').read_bytes()
        require(digest(apache)==APACHE_SHA,'Official Apache-2.0 text bytes differ')
        notice=(root/'src/pyelk/_licenses/NOTICE-GWT-Random.md').read_text(encoding='utf8')
        require(all(s in notice for s in ('Copyright 2009 Google Inc.','ASF','RICHARD ZSCHECH','JavaRandom',
                                         'exact external Java/GWT build identity remains unresolved')),
                'Random source attribution or exact-build limitation is missing')
        require('AND Apache-2.0' in (root/'src/pyelk/algorithms/layered/phases.py').read_text(encoding='utf8').splitlines()[0],
                'Mixed-source phase header omits Apache helper terms')
        expected=set(old)|ADDED
        actual={p.relative_to(root/'src/pyelk').as_posix() for p in (root/'src/pyelk').rglob('*')
                if p.is_file() and (p.suffix=='.py' or p.name=='py.typed' or '_licenses' in p.parts)}
        require(actual==expected and len(actual)==45,'Runtime/notice file denominator differs')
        license_files=sorted({p.relative_to(root).as_posix() for pattern in patterns for p in root.glob(pattern) if p.is_file()})
        return {'passed':True,'errors':[],'version':version,'licenseExpression':expression,
                'packageFilesSha256':{n:digest((root/'src/pyelk'/n).read_bytes()) for n in sorted(expected)},
                'licenseFilesSha256':{n:digest((root/n).read_bytes()) for n in license_files},
                'runtimeAstSha256':ast_hashes,'runtimeAstChanged':False,'versionLiteralMayChange':True,
                'sourceOnly':True,'fullValidation':False,'runtimeReexecuted':False}
    except (ValueError,KeyError,TypeError,AttributeError,OSError,SyntaxError) as error:
        return {'passed':False,'errors':[str(error)],'sourceOnly':True,'fullValidation':False,'runtimeReexecuted':False}


def check_artifacts(wheel,sdist,root=ROOT, *, require_stable=True):
    root=Path(root);result=check_source(root,require_stable=require_stable)
    if not result['passed']:return result
    try:
        with zipfile.ZipFile(wheel) as binary,tarfile.open(sdist) as source:
            names=binary.namelist();metadata_names=[n for n in names if n.endswith('.dist-info/METADATA')]
            require(len(metadata_names)==1 and len(names)==len(set(names)),'Ambiguous wheel entries/metadata')
            raw=binary.read(metadata_names[0]);metadata=BytesParser().parsebytes(raw)
            project=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf8'))['project']
            allowed_dev={x+'; extra == "dev"' for x in project.get('optional-dependencies',{}).get('dev',[])}
            require(metadata['Name']=='py-elk' and metadata['Version']==result['version'] and
                    metadata['License-Expression']==result['licenseExpression'] and metadata['Requires-Python']=='>=3.11' and
                    set(metadata.get_all('Requires-Dist',[]))==allowed_dev,
                    'Candidate metadata name/version/license/runtime dependencies differ')
            readme=(root/'README.md').read_bytes().replace(b'\r\n',b'\n')
            description=raw.replace(b'\r\n',b'\n').partition(b'\n\n')[2]
            require(description==readme,'Candidate README description differs from frozen source')
            require(set(metadata.get_all('License-File',[]))==set(result['licenseFilesSha256']),
                    'Candidate METADATA omits license/notice files')
            require({n[6:] for n in names if n.startswith('pyelk/') and not n.endswith('/')}==set(result['packageFilesSha256']),
                    'Wheel package file denominator differs')
            roots={PurePosixPath(m.name).parts[0] for m in source.getmembers()}
            require(len(roots)==1,'Ambiguous source archive root');prefix=next(iter(roots))+'/'
            for member in source.getmembers():
                p=PurePosixPath(member.name)
                require(not p.is_absolute() and '..' not in p.parts and not (member.issym() or member.islnk()),
                        'Unsafe or linked source archive member')
            for name,expected in result['packageFilesSha256'].items():
                stream=source.extractfile(prefix+'src/pyelk/'+name)
                require(stream is not None and digest(stream.read())==expected and digest(binary.read('pyelk/'+name))==expected,
                        'Source/wheel/current package file bytes differ: '+name)
            dist_info=metadata_names[0].split('/')[0]
            for name,expected in result['licenseFilesSha256'].items():
                stream=source.extractfile(prefix+name)
                require(stream is not None and digest(stream.read())==expected and
                        digest(binary.read(dist_info+'/licenses/'+name))==expected,'Candidate license bytes differ: '+name)
            require(source.extractfile(prefix+'PKG-INFO').read()==raw,'Source/wheel metadata bytes differ')
            require(source.extractfile(prefix+'pyproject.toml').read()==(root/'pyproject.toml').read_bytes(),
                    'Source archive project metadata differs')
            require(source.extractfile(prefix+'README.md').read().replace(b'\r\n',b'\n')==readme,
                    'Source archive README differs')
            require(all(PurePosixPath(n).suffix.lower() not in ('.js','.cjs','.mjs','.jar','.wasm') for n in names),
                    'Unexpected executable layout backend in wheel')
        return {**result,'sourceOnly':False,'wheelSha256':digest(Path(wheel).read_bytes()),
                'sdistSha256':digest(Path(sdist).read_bytes()),'metadataSha256':digest(raw),'sameCandidateBytes':True}
    except (ValueError,KeyError,TypeError,AttributeError,OSError,zipfile.BadZipFile,tarfile.TarError) as error:
        return {**result,'passed':False,'errors':[str(error)],'sourceOnly':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-only',action='store_true')
    parser.add_argument('--wheel',type=Path);parser.add_argument('--sdist',type=Path);parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if not args.source_only and (args.wheel is None or args.sdist is None):parser.error('Use --source-only or both --wheel/--sdist')
    value=check_source() if args.source_only else check_artifacts(args.wheel,args.sdist)
    value['verifierSha256']=digest(Path(__file__).read_bytes())
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x',encoding='utf8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(value));return 0 if value['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
