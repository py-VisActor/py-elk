"""Verify a published release against the actual accepted upload artifacts.

Read-only: never uploads. Index absence, extra distributions, metadata drift or
digest mismatches are failures. Installation occurs only after both downloaded
files match the supplied original artifacts. Plan mode performs no network IO.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import quote,urlsplit
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_full_package import artifact_kind,canonical_project_name,project_metadata


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def require(condition,message):
    if not condition:raise ValueError(message)


def verify_index(index,version,expected,*,project=None):
    project=project_metadata()['name']if project is None else project
    normalized=canonical_project_name(project)
    kinds={name:artifact_kind(name,project,version)for name in expected}
    require(len(kinds)==2 and set(kinds.values())=={'bdist_wheel','sdist'},'Expected one wheel and one sdist')
    info=index['info']
    require(canonical_project_name(info['name'])==normalized,'PyPI project identity differs')
    require(info['version']==version,'PyPI version differs')
    require(info['requires_python']=='>=3.11','Python requirement differs')
    require(all('extra =='in row for row in(info.get('requires_dist')or[])),
            'Unexpected mandatory runtime dependency')
    files=index['urls'];names=[row['filename']for row in files]
    require(len(names)==len(set(names))and set(names)==set(expected),'Published file set differs')
    result={}
    for row in files:
        name=row['filename'];url=urlsplit(row['url'])
        require(row.get('packagetype')==kinds[name],'Distribution archive type differs: '+name)
        require(url.scheme=='https'and url.hostname=='files.pythonhosted.org'and not url.username,
                'Unexpected distribution URL')
        require(row['digests']['sha256']==expected[name],'Published SHA256 differs: '+name)
        require(row.get('yanked',False)is False,'Distribution is yanked')
        require(Path(name).name==name and '\\'not in name,'Unsafe distribution filename')
        result[name]=row
    return result


def plan(version,project=None):
    project=project_metadata()['name']if project is None else project
    project=canonical_project_name(project)
    return {'schema':'py-elk-pypi-release-plan/v1','version':version,
            'project':project,'importPackage':'pyelk',
            'index':'https://pypi.org/pypi/'+quote(project,safe='')+'/'+quote(version,safe='')+'/json',
            'expectedArtifacts':'Use exact accepted/uploaded wheel and sdist, including a workflow rebuild if one occurred',
            'steps':['verify index metadata and exact published hashes','download both files into a new directory',
                     'verify downloaded bytes against originals','isolated wheel/sdist payload and real layout check'],
            'publishes':False,'networkRequestsExecuted':0,'layoutExecutions':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-only',action='store_true');parser.add_argument('--version',default='0.1.0')
    parser.add_argument('--project',help='Expected PyPI project; default: current pyproject.toml')
    parser.add_argument('--expected-wheel',type=Path);parser.add_argument('--expected-sdist',type=Path)
    parser.add_argument('--out',type=Path);args=parser.parse_args()
    project=project_metadata()['name']if args.project is None else args.project
    project=canonical_project_name(project)
    if args.plan_only:print(json.dumps(plan(args.version,project),indent=2));return 0
    if any(value is None for value in(args.expected_wheel,args.expected_sdist,args.out)):
        parser.error('--expected-wheel, --expected-sdist and --out are required')
    args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    expected={p.name:digest(p)for p in(args.expected_wheel,args.expected_sdist)}
    report={'schema':'py-elk-pypi-release-verification/v1','version':args.version,
            'project':project,'importPackage':'pyelk',
            'expectedArtifactsSha256':expected,'publishedByThisTool':False,'passed':False}
    try:
        request=Request(plan(args.version,project)['index'],headers={'User-Agent':project+'-release-verifier'})
        try:
            with urlopen(request,timeout=30)as response:raw=response.read()
        except HTTPError as error:
            report.update(status='PYPI_RELEASE_NOT_AVAILABLE',httpStatus=error.code,error=str(error))
            save(args.out/'report.json',report);print(json.dumps(report));return 2
        (args.out/'index.json').write_bytes(raw);index=json.loads(raw)
        files=verify_index(index,args.version,expected,project=project)
        report['indexSha256']=hashlib.sha256(raw).hexdigest();downloaded={}
        for name,row in files.items():
            target=args.out/name
            with urlopen(row['url'],timeout=60)as response,target.open('xb')as output:
                while chunk:=response.read(1024*1024):output.write(chunk)
            require(digest(target)==expected[name],'Downloaded SHA256 differs: '+name)
            downloaded[name]=target
        command=[sys.executable,str(ROOT/'scripts/validate_full_package.py'),'--wheel',
                 str(downloaded[args.expected_wheel.name]),'--sdist',str(downloaded[args.expected_sdist.name]),
                 '--out',str(args.out/'installed')]
        command.extend(['--project',project])
        process=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180)
        (args.out/'install.stdout.log').write_bytes(process.stdout)
        (args.out/'install.stderr.log').write_bytes(process.stderr)
        report['installationCommand']={'argv':command,'exitCode':process.returncode}
        require(process.returncode==0,'Downloaded release installation/layout failed')
        installed=json.loads((args.out/'installed/summary.json').read_bytes())
        require(installed['passed']is True,'Downloaded installation receipt did not pass')
        report.update(passed=True,status='PUBLISHED_DOWNLOAD_AND_INSTALL_VERIFIED',
                      releaseURL='https://pypi.org/project/'+quote(project,safe='')+'/'+quote(args.version,safe='')+'/',
                      installedSummarySha256=digest(args.out/'installed/summary.json'))
    except Exception as error:report.update(status='FAIL',error=type(error).__name__+': '+str(error))
    save(args.out/'report.json',report)
    print(json.dumps({key:report.get(key)for key in('passed','status','error','releaseURL')}))
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
