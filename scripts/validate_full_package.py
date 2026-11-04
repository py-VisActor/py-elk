"""Check full native wheel/sdist payloads and execute an isolated installation.

Archives are checked against current source bytes. This is not a publication
or download verification and does not replace algorithm/platform acceptance.
"""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SMOKE='''import asyncio,importlib,importlib.metadata,pathlib,json
from pyelk import ELK,__version__
import pyelk
DIST_NAME=__DIST_NAME__
async def main():
    graph={'id':'root','business':{'retained':True},
           'layoutOptions':{'algorithm':'layered','randomSeed':42},
           'children':[{'id':str(i),'width':20,'height':15}for i in range(20)],
           'edges':[{'id':'e'+str(i),'sources':[str(i)],'targets':[str(i+1)]}for i in range(19)]}
    with ELK(timeout=30)as elk:
        sizes=[len(await elk.knownLayoutAlgorithms()),len(await elk.knownLayoutOptions()),len(await elk.knownLayoutCategories())]
        assert sizes==[12,243,8],sizes
        result=await elk.layout(graph)
        assert result['business']==graph['business']
        assert len(result['children'])==20 and result['width']>0
        assert all(edge.get('sections')for edge in result['edges'])
    package=pathlib.Path(pyelk.__file__).parent
    modules=[]
    for path in sorted(package.rglob('*.py')):
        name='pyelk.'+path.relative_to(package).as_posix()[:-3].replace('/','.')
        if name.endswith('.__init__'):name=name[:-9]
        importlib.import_module(name);modules.append(name)
    distribution_name=importlib.metadata.metadata(DIST_NAME)['Name']
    print(json.dumps({'version':__version__,'distributionName':distribution_name,'package':str(package),'modules':len(modules),
                      'metadata':sizes,'nodes':len(result['children']),'passed':True}))
if __name__=='__main__':asyncio.run(main())
'''


def require(value,message):
    if not value:raise ValueError(message)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def project_metadata():
    return tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))['project']


def canonical_project_name(value):
    """PyPA name comparison, distinct from the unchanged pyelk import name."""
    require(type(value)is str and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?',value),
            'Invalid distribution project name')
    return re.sub(r'[-_.]+','-',value).lower()


def artifact_kind(filename,project,version):
    """Require canonical normalized names for this release's wheel and sdist."""
    require(type(filename)is str and Path(filename).name==filename and '\\'not in filename,
            'Unsafe distribution filename')
    name=canonical_project_name(project).replace('-','_')
    require(type(version)is str and re.fullmatch(r'[A-Za-z0-9.!+_]+',version),
            'Invalid release filename version')
    if filename==name+'-'+version+'.tar.gz':return'sdist'
    if filename.endswith('.whl'):
        parts=filename[:-4].split('-')
        require(len(parts)in(5,6)and parts[:2]==[name,version],
                'Wheel normalized project/version differs')
        require(all(re.fullmatch(r'[A-Za-z0-9_.]+',part)for part in parts[-3:]),
                'Malformed wheel compatibility tag')
        if len(parts)==6:require(re.fullmatch(r'[0-9][A-Za-z0-9_]*',parts[2]),'Malformed wheel build tag')
        return'bdist_wheel'
    raise ValueError('Expected canonical wheel or .tar.gz sdist filename')


def require_metadata_identity(metadata,project,version):
    require(canonical_project_name(metadata['Name'])==canonical_project_name(project)
            and metadata['Version']==version,'Package identity differs')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',required=True,type=Path)
    parser.add_argument('--sdist',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--project',help='Expected distribution name; default: current pyproject.toml')
    parser.add_argument('--install-kind',choices=('wheel','sdist'),default='wheel',
                        help='Actually install this archive kind in the isolated environment')
    parser.add_argument('--wheelhouse',type=Path,
                        help='Offline build dependencies, required for a source installation')
    parser.add_argument('--exercise-mrtree-cycle',type=Path,
                        help='Also require this known cyclic Walker request to raise RecursionError')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    if args.install_kind=='sdist'and args.wheelhouse is None:
        parser.error('--install-kind sdist requires --wheelhouse')
    expected={p.relative_to(ROOT/'src').as_posix():p.read_bytes()
              for p in (ROOT/'src/pyelk').rglob('*')if p.is_file()and'__pycache__'not in p.parts
              and(p.suffix=='.py'or p.name=='py.typed'or'_licenses'in p.parts)}
    project=project_metadata()
    distribution=args.project if args.project is not None else project['name']
    require(artifact_kind(args.wheel.name,distribution,project['version'])=='bdist_wheel','--wheel is not a wheel')
    require(artifact_kind(args.sdist.name,distribution,project['version'])=='sdist','--sdist is not a source archive')
    with zipfile.ZipFile(args.wheel)as archive:
        names=archive.namelist();require(len(names)==len(set(names)),'Duplicate wheel entry')
        payload={name:archive.read(name)for name in names if name.startswith('pyelk/')}
        require(payload==expected,'Wheel runtime source/license payload differs from current source')
        metadata_names=[name for name in names if name.endswith('.dist-info/METADATA')]
        require(len(metadata_names)==1,'Expected one wheel metadata file')
        metadata=BytesParser().parsebytes(archive.read(metadata_names[0]))
        require_metadata_identity(metadata,distribution,project['version'])
        require(metadata_names[0]==canonical_project_name(distribution).replace('-','_')+'-'+project['version']+'.dist-info/METADATA',
                'Wheel metadata directory identity differs')
        require(metadata['License-Expression']==project['license'],'License expression differs')
        require(metadata['Requires-Python']==project['requires-python'],'Python requirement differs')
        require(not metadata.get_all('Requires-Dist',[])
                or all('extra =='in value for value in metadata.get_all('Requires-Dist',[])),
                'Unexpected runtime dependency')
        licenses=[name for name in names if '.dist-info/licenses/'in name]
        require(any(name.endswith('/LICENSE')and archive.read(name)==(ROOT/'LICENSE').read_bytes()
                    for name in licenses),'Root MIT license absent from wheel')
    with tarfile.open(args.sdist,'r:gz')as archive:
        members=archive.getmembers();prefix=members[0].name.split('/')[0]+'/'
        require(prefix==args.sdist.name[:-7]+'/','Sdist top-level directory identity differs')
        require_metadata_identity(BytesParser().parsebytes(archive.extractfile(prefix+'PKG-INFO').read()),
                                  distribution,project['version'])
        payload={m.name[len(prefix+'src/'):]:archive.extractfile(m).read()
                 for m in members if m.isfile()and m.name.startswith(prefix+'src/pyelk/')}
        require(payload==expected,'Sdist runtime source/license payload differs')
        require(archive.extractfile(prefix+'pyproject.toml').read()==(ROOT/'pyproject.toml').read_bytes(),
                'Sdist build configuration differs')
    commands=[]
    with tempfile.TemporaryDirectory(prefix='pyelk-full-install-')as temp:
        folder=Path(temp);environment=folder/'venv';venv.EnvBuilder(with_pip=True).create(environment)
        python=environment/('Scripts/python.exe'if sys.platform=='win32'else'bin/python')
        smoke_text=SMOKE.replace('__DIST_NAME__',repr(distribution))
        if args.exercise_mrtree_cycle is not None:
            request_raw=args.exercise_mrtree_cycle.read_bytes()
            request_path=folder/'mrtree-cycle-request.json';request_path.write_bytes(request_raw)
            extra='''    request=json.loads(pathlib.Path(__file__).with_name('mrtree-cycle-request.json').read_bytes())
    with ELK(timeout=10) as elk:
        try:
            await elk.layout(request['graph'], request.get('layoutArguments', {}))
        except RecursionError as error:
            assert 'MrTree second walk' in str(error), str(error)
            cycle={'type':type(error).__name__,'message':str(error)}
        else:
            raise AssertionError('Cyclic MrTree Walker request unexpectedly returned')
'''
            smoke_text=smoke_text.replace('    package=pathlib.Path(pyelk.__file__).parent',
                                          extra+'    package=pathlib.Path(pyelk.__file__).parent')
            smoke_text=smoke_text.replace("'passed':True}))", "'passed':True,'mrtreeCycle':cycle}))")
        smoke=folder/'installed_smoke.py';smoke.write_text(smoke_text,encoding='utf-8')
        planned=[]
        if args.install_kind=='sdist':
            planned.append(('build-deps',[str(python),'-I','-m','pip','install','--no-index','--no-deps',
                            '--find-links',str(args.wheelhouse.resolve()),'setuptools==84.2.1',
                            'wheel==0.48.0','packaging==26.3']))
        artifact=args.wheel if args.install_kind=='wheel'else args.sdist
        planned.append(('install',[str(python),'-I','-m','pip','install','--disable-pip-version-check',
                                   '--no-index','--no-deps',*(['--no-build-isolation']if args.install_kind=='sdist'else[]),
                                   str(artifact.resolve())]))
        planned.append(('smoke',[str(python),'-I',str(smoke)]))
        for name,command in planned:
            result=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=120)
            (args.out/(name+'.stdout.log')).write_text(result.stdout,encoding='utf-8')
            (args.out/(name+'.stderr.log')).write_text(result.stderr,encoding='utf-8')
            commands.append({'name':name,'command':command,'exitCode':result.returncode})
            require(result.returncode==0,name+' failed: '+result.stderr[-2000:])
        installed=json.loads(result.stdout)
        require(Path(installed['package']).is_relative_to(environment),'Smoke imported outside isolated environment')
        require(canonical_project_name(installed['distributionName'])==canonical_project_name(distribution),
                'Installed distribution metadata identity differs')
    report={'schema':'py-elk-full-package-validation/v1','passed':True,
            'project':canonical_project_name(distribution),'importPackage':'pyelk',
            'distributionName':installed['distributionName'],
            'wheelSha256':digest(args.wheel.read_bytes()),'sdistSha256':digest(args.sdist.read_bytes()),
            'installKind':args.install_kind,'artifactSha256':digest(artifact.read_bytes()),
            'runtimeFilesSha256':{name:digest(raw)for name,raw in sorted(expected.items())},
            'commands':commands,'installedObservation':installed,'published':False,
            'fullAlgorithmAcceptance':False}
    if args.exercise_mrtree_cycle is not None:
        report['mrtreeCycleRequestSha256']=digest(request_raw)
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'runtimeFiles':len(expected),'installed':installed}))


if __name__=='__main__':main()
