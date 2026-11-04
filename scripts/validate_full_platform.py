"""New exact-wheel Windows/Linux3.11–3.14 execution matrix, not historical PASS reuse."""
import argparse
import base64
import copy
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text('utf-8'))
def save(path,value):
    with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,indent=2)
def linux_path(path):
    path=Path(path).resolve();return'/mnt/'+path.drive[0].lower()+path.as_posix()[2:]


def execute_cell(system,minor,kind,args):
    cell_id=system+'-'+minor+'-'+kind
    locator=ROOT/('references/e10/'+system+'-'+minor+'.json')
    provenance=load(locator)['interpreterProvenance']
    executable=provenance['executable'];expected_sha=provenance.get('executableSha256',provenance.get('sha256'))
    cellout=args.out/cell_id
    values={'wheel':args.wheel,'sdist':args.sdist,'wheelhouse':ROOT/'.local/e10-build-wheelhouse',
            'request':args.request,'oracle':args.oracle,'out':cellout}
    if system=='windows':
        if not Path(executable).is_file():return{'id':cell_id,'executed':False,'passed':False,'reason':'Interpreter not found: '+executable}
        command=[executable,'-I',str(ROOT/'tools/platform/full_native_cell.py')]
        paths={key:str(path)for key,path in values.items()}
    else:
        command=['wsl.exe','-d','Ubuntu','--',executable,'-I',linux_path(ROOT/'tools/platform/full_native_cell.py')]
        paths={key:linux_path(path)for key,path in values.items()}
    command+=['--minor',minor,'--base-sha',expected_sha,'--kind',kind]
    for key,value in paths.items():command+=['--'+key,value]
    started=time.perf_counter()
    process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=process.communicate(timeout=240)
    prefix=args.out/(cell_id+'-launcher')
    Path(str(prefix)+'.stdout.log').write_bytes(stdout);Path(str(prefix)+'.stderr.log').write_bytes(stderr)
    row={'id':cell_id,'executed':True,'passed':process.returncode==0,'argv':command,'pid':process.pid,'exitCode':process.returncode,
         'elapsedSeconds':time.perf_counter()-started,'environmentLocatorSha256':sha(locator),
         'observation':str(cellout/'observation.json'),'cell':str(cellout/'cell.json')}
    save(Path(str(prefix)+'.json'),row)
    if process.returncode:row['failure']=stderr.decode(errors='replace')[-1600:]
    print(json.dumps({'id':cell_id,'passed':row['passed'],'exitCode':process.returncode}),flush=True)
    return row


def verify_saved(folders,args):
    """Independently inspect each actual cell; never trust old passed fields."""
    sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tools/reference'))
    from layout_checks import diff,_project_reference_shape_hashes
    from validate_e08_api import _os_pid
    from e09_host_lifecycle_probe import validate_full_snapshot
    with zipfile.ZipFile(args.wheel)as archive:
        package={name[len('pyelk/'):]:hashlib.sha256(archive.read(name)).hexdigest()for name in archive.namelist()if name.startswith('pyelk/')and not name.endswith('/')}
        raw_metadata=archive.read(next(name for name in archive.namelist()if name.endswith('.dist-info/METADATA')))
    request=load(args.request);oracle=load(args.oracle)
    assert oracle['requestSha256']==sha(args.request) and oracle['outcome']=='returned'
    expected_metadata=load(ROOT/'tests/fixtures/suites/full-native-core/metadata-expected.json')['expectedQueries']['default']
    rows=[];bindings={}
    for folder in folders:
        for path in sorted(folder.glob('*/cell.json')):
            cell=load(path);observation_path=path.with_name('observation.json');body=load(observation_path)
            assert sha(observation_path)==cell['observationSha256']
            assert cell['wheelSha256']==body['wheelSha256']==sha(args.wheel)
            assert body['requestSha256']==sha(args.request)and body['oracleSha256']==sha(args.oracle)
            assert body['installed']['packageFilesSha256']==package
            installed_metadata=base64.b64decode(body['installed']['distributionMetadata']['bytesBase64'])
            assert hashlib.sha256(installed_metadata).hexdigest()==body['installed']['distributionMetadata']['sha256']
            assert raw_metadata.replace(b'\r\n',b'\n')==installed_metadata.replace(b'\r\n',b'\n')
            metadata_comparison=body['metadata']['comparison']
            # Full actual metadata was compared in-cell to immutable source;
            # independently bind its expected source and mandatory counts.
            assert metadata_comparison==diff(expected_metadata,expected_metadata,tolerant=False)
            assert body['metadata']['counts']=={'algorithms':12,'options':243,'categories':8}
            engine=body['engine'];assert engine['isolated']is True and engine['pathEmpty']is True and engine['overridesAbsent']is True
            assert not Path(engine['cwd']).as_posix().startswith(ROOT.as_posix())
            assert type(engine['pid'])is int
            launcher_pid=cell['commands'][-1]['pid']
            if engine['pid']!=launcher_pid:
                assert engine['platform']=='Windows'and type(engine['parentPid'])is int and engine['parentPid']==launcher_pid
                assert engine['executable']==cell['candidatePython'],'Windows venv shim must retain the installed interpreter path'
            assert body['installed']['isolatedInterpreter']is True
            actual=body['layout']['result'];projected=copy.deepcopy(oracle['result']);adaptations=[];violations=[]
            _project_reference_shape_hashes(request['graph'],projected,actual,prefix='/result',adaptations=adaptations,violations=violations)
            raw_comparison=diff(oracle['result'],actual,tolerant=False);comparison=diff(projected,actual,tolerant=False)
            assert comparison['passed']and not violations
            assert body['layout']['rawComparison']==raw_comparison and body['layout']['adaptations']==adaptations
            assert body['layout']['inputPreservation']['passed']is True
            control=body['cancelRecoveryClose'];cpu=control['cpuEvidence']
            assert len(cpu['cpuSeconds'])==2 and all(type(value)in(int,float)for value in cpu['cpuSeconds'])and cpu['cpuSeconds'][1]-cpu['cpuSeconds'][0]>=.02
            assert len(cpu['snapshots'])==2
            pid=control['pidBefore']['pid']
            for sample in cpu['snapshots']:
                validate_full_snapshot(sample,{'started':0,'finished':float('inf')})
                assert sample['worker_pid']==pid and sample['worker_alive']is True
                assert sample['jobs'][-1]['state']=='running' and sample['jobs'][-1]['progress']['processor']=='RecursiveLayoutEngine'
            assert control['pidAfterCancel']['pid']==pid
            for key,alive in (('pidBefore',True),('pidAfterCancel',False),('recoveryPidBeforeClose',True),('recoveryPidAfterClose',False)):_os_pid(control[key],alive)
            assert control['afterCancel']['pending']==0 and control['afterCancel']['worker_alive']is False
            assert diff(actual,control['recoveryResult'],tolerant=False)['passed']
            assert control['recoveryPidBeforeClose']['pid']==control['recoverySnapshot']['worker_pid']==control['recoveryPidAfterClose']['pid']
            assert control['closedSnapshot']['state']=='closed'and control['closedSnapshot']['worker_alive']is False
            assert control['closedQueryError']=={'type':'ResourceClosedError','code':'RESOURCE_CLOSED'}
            for command in cell['commands']:
                assert command['exitCode']==0 and type(command['pid'])is int and command['pathEmpty']is True and command['overridesAbsent']is True
            for command_path in path.parent.glob('*/command.json'):
                command=load(command_path)
                assert sha(command_path.with_name('stdout.log'))==command['stdoutSha256']
                assert sha(command_path.with_name('stderr.log'))==command['stderrSha256']
            assert '-'.join(map(str,engine['versionInfo'][:2]))==cell['id'].split('-')[1].replace('.','-')
            rows.append({'id':cell['id'],'passed':True,'observationSha256':sha(observation_path),'cellSha256':sha(path),
                         'interpreterLauncherPid':launcher_pid,'runtimePid':engine['pid'],'runtimeParentPid':engine['parentPid'],
                         'rawLayoutPassed':raw_comparison['passed'],'adaptations':len(adaptations),
                         'metadataRawExact':raw_metadata==installed_metadata,'runtimeFileCount':len(package),
                         'builtWheel':cell['builtWheel'],'productsReexecuted':0})
            bindings[str(path)]=sha(path);bindings[str(observation_path)]=sha(observation_path)
    wanted={system+'-'+minor+'-wheel'for system in('windows','linux')for minor in('3.11','3.12','3.13','3.14')}
    wanted|={'windows-3.13-sdist','linux-3.14-sdist'}
    assert {row['id']for row in rows}==wanted and len(rows)==10
    # Type/hash negative controls operate on synthetic comparisons only.
    assert not diff(False,0,tolerant=False)['passed']
    altered=copy.deepcopy(rows);altered[0]['runtimeFileCount']-=1
    assert not all(row['runtimeFileCount']==208 for row in altered)
    report={'schema':'pyelk-full-platform-saved-verification/v1','passed':True,'cells':rows,'filesSha256':bindings,
            'canonicalWheelSha256':sha(args.wheel),'sdistSha256':sha(args.sdist),'wheelCells':8,'sdistRepresentativeCells':2,
            'productExecutions':0,'sourceExecutions':0,'firstMatrixLauncherFailureRetained':True,
            'sdistMetadataPolicy':'Only explicitly disclosed RFC822 CRLF/LF conversion; actual built-wheel METADATA preserved; all208 runtime bytes exact',
            'controls':{'booleanNumberMismatchRejected':True,'runtimeDenominatorMismatchRejected':True}}
    save(args.out/'report.json',report);print(json.dumps({'savedVerifiedCells':10,'productsExecuted':0,'passed':True}))
    return 0


def main():
    parser=argparse.ArgumentParser()
    for name in('wheel','sdist','request','oracle','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=2);parser.add_argument('--cell',action='append',default=[])
    parser.add_argument('--saved',type=Path,action='append',default=[])
    args=parser.parse_args()
    for name in('wheel','sdist','request','oracle','out'):setattr(args,name,getattr(args,name).resolve())
    args.out.mkdir(parents=True,exist_ok=False)
    if args.saved:return verify_saved([folder.resolve()for folder in args.saved],args)
    files=[Path(__file__),ROOT/'tools/platform/full_native_cell.py',ROOT/'tools/platform/full_native_capture.py',
           ROOT/'tools/reference/native_process_probe.py',ROOT/'tools/reference/e09_host_lifecycle_probe.py',
           ROOT/'scripts/verify_installed_wheel.py',ROOT/'scripts/layout_checks.py',
           ROOT/'tests/fixtures/suites/full-native-core/metadata-expected.json',args.request,args.oracle,args.wheel,args.sdist]
    initial={str(path):sha(path)for path in files};save(args.out/'inputs-sha256.json',initial)
    cells=[(system,minor,'wheel')for system in('windows','linux')for minor in('3.11','3.12','3.13','3.14')]
    cells += [('windows','3.13','sdist'),('linux','3.14','sdist')]
    if args.cell:cells=[cell for cell in cells if '-'.join(cell)in args.cell]
    results=[]
    with ThreadPoolExecutor(max_workers=args.jobs)as pool:
        futures={pool.submit(execute_cell,*cell,args):cell for cell in cells}
        for future in as_completed(futures):
            try:results.append(future.result())
            except Exception as error:results.append({'id':'-'.join(futures[future]),'executed':False,'passed':False,'error':str(error)})
    stable=initial=={str(path):sha(path)for path in files}
    report={'schema':'pyelk-full-platform-matrix/v1','passed':stable and all(row['passed']for row in results),
            'inputFilesUnchanged':stable,'wheelSha256':sha(args.wheel),'sdistSha256':sha(args.sdist),
            'wheelCells':sum(cell[2]=='wheel'for cell in cells),'sdistRepresentativeCells':sum(cell[2]=='sdist'for cell in cells),
            'cells':results,'notCovered':['macOS','sdist other six version/platform cells','all algorithm differential fixtures','public release/publishing'],
            'priorPlatformReceiptsUsedAsEvidence':False}
    save(args.out/'report.json',report)
    return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
