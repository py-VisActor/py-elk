"""Build a fresh external venv, install exact artifact, capture in isolation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
OVERRIDES={'PYTHONPATH','PYTHONHOME','NODE_OPTIONS','NODE_PATH'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,indent=2)


def run(argv,cwd,folder):
    folder.mkdir();env={k:v for k,v in os.environ.items()if k.upper()not in OVERRIDES};env['PATH']=''
    started=time.perf_counter();process=subprocess.Popen(list(map(str,argv)),cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:stdout,stderr=process.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        process.kill();stdout,stderr=process.communicate();raise RuntimeError('Cell subprocess exceeded180s')
    (folder/'stdout.log').write_bytes(stdout);(folder/'stderr.log').write_bytes(stderr)
    record={'argv':list(map(str,argv)),'cwd':str(cwd),'pid':process.pid,'exitCode':process.returncode,
            'elapsedSeconds':time.perf_counter()-started,'pathEmpty':True,'overridesAbsent':True,
            'stdoutSha256':hashlib.sha256(stdout).hexdigest(),'stderrSha256':hashlib.sha256(stderr).hexdigest()}
    save(folder/'command.json',record)
    if process.returncode:raise RuntimeError('Actual command failed: '+str(folder)+'\n'+stderr.decode(errors='replace')[-2000:])
    return record


def main(args):
    args.out.mkdir(parents=True,exist_ok=False)
    work=Path(tempfile.mkdtemp(prefix='pyelk-full-'+args.minor+'-')).resolve()
    if work.is_relative_to(ROOT):raise RuntimeError('Cell workspace must be outside repository')
    assert '.'.join(map(str,sys.version_info[:2]))==args.minor
    assert sha(sys.executable)==args.base_sha
    commands=[]
    commands.append(run([sys.executable,'-I','-m','venv',work/'runtime'],work,args.out/'venv'))
    relative='Scripts/python.exe'if os.name=='nt'else'bin/python'
    candidate=work/'runtime'/relative;artifact=args.wheel;built=None
    if args.kind=='sdist':
        commands.append(run([sys.executable,'-I','-m','venv',work/'build'],work,args.out/'build-venv'))
        builder=work/'build'/relative
        commands.append(run([builder,'-I','-m','pip','install','--no-index','--find-links',args.wheelhouse,
                             'setuptools==84.2.1','wheel==0.48.0','packaging==26.3'],work,args.out/'build-dependencies'))
        commands.append(run([builder,'-I','-m','pip','wheel','--no-index','--no-deps','--no-build-isolation',
                             '--wheel-dir',work/'built',args.sdist],work,args.out/'build-sdist'))
        wheels=list((work/'built').glob('*.whl'));assert len(wheels)==1
        artifact=wheels[0];built={'path':str(artifact),'sha256':sha(artifact),'sdistSha256':sha(args.sdist)}
    commands.append(run([candidate,'-I','-m','pip','install','--no-index','--no-deps',artifact],work,args.out/'install'))
    save(args.out/'installation.json',{'candidatePython':str(candidate),'externalWorkspace':str(work),'builtWheel':built,
         'canonicalWheelSha256':sha(args.wheel),'artifactKind':args.kind,'installedWheel':str(artifact),'installedWheelSha256':sha(artifact)})
    commands.append(run([candidate,'-I',ROOT/'tools/platform/full_native_capture.py','--wheel',args.wheel,
                         '--installed-wheel',artifact,
                         '--request',args.request,'--oracle',args.oracle,'--out',args.out/'observation.json'],work,args.out/'capture'))
    observation=json.loads((args.out/'observation.json').read_text('utf-8'))
    assert observation['engine']['versionInfo'][:2]==list(map(int,args.minor.split('.')))
    result={'schema':'pyelk-full-platform-cell/v1','id':platform.system().lower()+'-'+args.minor+'-'+args.kind,
            'passed':observation['passed'],'wheelSha256':sha(args.wheel),'artifactKind':args.kind,
            'artifactSha256':sha(args.sdist if args.kind=='sdist'else args.wheel),'builtWheel':built,
            'baseExecutable':sys.executable,'baseExecutableSha256':sha(sys.executable),'baseVersion':sys.version,
            'candidatePython':str(candidate),'externalWorkspace':str(work),'commands':commands,
            'observationSha256':sha(args.out/'observation.json')}
    save(args.out/'cell.json',result);print(json.dumps({'cell':result['id'],'passed':result['passed']}))
    return 0 if result['passed']else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--minor',required=True);parser.add_argument('--base-sha',required=True)
    parser.add_argument('--kind',choices=('wheel','sdist'),required=True)
    for name in('wheel','sdist','wheelhouse','request','oracle','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:raise SystemExit(main(args))
    except Exception as error:
        args.out.mkdir(parents=True,exist_ok=True)
        save(args.out/'failure.json',{'type':type(error).__name__,'message':str(error)})
        raise
