"""Pure targeted E10 platform checks; never launches layout or a full suite.

Capture dependencies are recorded by the collector. This verifier's current
identity belongs to a new report, never to a rewritten old execution receipt.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from layout_checks import load,sha256,geometry,contained
from validate_e04_runtime import embedded_json,exact
from validate_e08_api import NATIVE_PROCESSORS,validate_snapshot,_os_pid,native_metadata_contract
from validate_e09_coverage import (compare_case,decode_capture,semantic,expectations,
    validate_installed_identity,validate_process_identity)

SUITE='tests/fixtures/suites/E10'
COLLECTOR='tools/platform/capture_e10.py'
EXPECTED_IDS=('layered-empty','layered-chain','layered-diamond-up-flags-11','generated-07',
              'error-unknown-endpoint','error-unknown-algorithm')
MINORS=('3.11','3.12','3.13','3.14')
SDIST_SHA='6fe04b1725955673d46b1e8dbdca3dc94cd81308b5276038e2ab2e2a4e1bd3ce'

def require(condition,message):
    if not condition:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def raw64(value):return base64.b64decode(value,validate=True)
def finite(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except (ValueError,OverflowError):return False
def path(value):
    require(type(value) is str and bool(value),'Absolute historical path missing')
    result=PureWindowsPath(value) if '\\' in value or re.match(r'^[A-Za-z]:',value) else PurePosixPath(value)
    require(result.is_absolute() and '..' not in result.parts,'Historical path must be absolute without parent traversal')
    return result

def execution_dependencies(root=ROOT):
    root=Path(root);suite=load(root/SUITE/'cases.json')
    require(suite['schema']=='py-elk-e10-platform-suite/v1' and
            [c['id'] for c in suite['cases']]==list(EXPECTED_IDS),'Frozen six platform cases differ')
    names=[COLLECTOR,'scripts/verify_installed_wheel.py',SUITE+'/cases.json',
           *[SUITE+'/'+c['request'] for c in suite['cases']],suite['cancelRequest']['path']]
    require(len(names)==10 and len(set(names))==10,'Platform capture dependency denominator differs')
    return {name:sha256(root/name) for name in names}

def check_command(wrapper):
    command=wrapper['command']
    exact(command['exitCode'],0,'Actual platform command failed');exact(command['timedOut'],False,'Platform command timed out')
    require(finite(command['elapsedSeconds']) and command['elapsedSeconds']>=0,'Invalid actual command elapsed time')
    for stream in ('stdout','stderr'):
        require(digest(raw64(wrapper[stream+'BytesBase64']))==command[stream+'Sha256'],'Original command log bytes differ')
    return command

def installation_source(value,engine,source):
    """Link actual offline pip/venv commands to wheel or the fixed source archive."""
    installed=value['installation'];create=check_command(installed['venvCommand'])
    install=check_command(installed['installCommand']);prefix=path(engine['prefix'])
    require(len(create['argv'])==5 and create['argv'][1:]==['-I','-m','venv',str(prefix)],'Actual fresh venv creation role differs')
    path(create['argv'][0])
    require(not path(create['cwd']).is_relative_to(source) and not path(install['cwd']).is_relative_to(source),'Installation ran inside checkout')
    common=[value['candidatePython'],'-I','-m','pip','install','--no-index','--no-deps']
    kind=installed['artifactKind']
    if kind=='wheel':
        require(installed['artifactSha256']==value['wheelSha256'],'Installed wheel source SHA differs')
        exact(install['argv'],[*common,value['wheel']],'Actual wheel installation argv differs')
        if 'artifact' in installed:require(path(installed['artifact'])==path(value['wheel']),'Wheel artifact path differs')
    elif kind=='sdist':
        require(installed['artifactSha256']==SDIST_SHA,'Source archive is not the locked E10 artifact')
        if 'buildCommand' in installed:
            build=check_command(installed['buildCommand']);argv=build['argv'];archive=installed.get('sourceArchive',installed.get('artifact'))
            require(type(archive) is str and len(argv)==11 and argv[1:9]==['-I','-m','pip','wheel','--no-index','--no-deps','--no-build-isolation','--wheel-dir'] and
                    path(argv[-1])==path(archive) and path(value['wheel']).parent==path(argv[-2]),'Actual source-to-wheel build role differs')
            require(not path(build['cwd']).is_relative_to(source),'Source build ran inside checkout')
            build_create=check_command(installed['buildVenvCommand']);build_prefix=path(build_create['argv'][-1])
            require(len(build_create['argv'])==5 and build_create['argv'][1:4]==['-I','-m','venv'] and
                    path(argv[0]).is_relative_to(build_prefix),'Source build interpreter is not the recorded fresh build venv')
            require(installed['builtWheelSha256']==value['wheelSha256'],'Built wheel/source install identity differs')
            exact(install['argv'],[*common,value['wheel']],'Actual built source wheel installation differs')
        else:
            archive=installed.get('artifact',install['argv'][-1]);path(archive)
            exact(install['argv'],[*common,'--no-build-isolation',archive],'Actual direct source installation argv differs')
        require(str(archive).endswith('.tar.gz'),'Source installation does not point at the locked archive kind')
    else:raise ValueError('Unknown actual installation artifact kind')

def closed_snapshot(value,interval):
    """Generic terminal case state; non-RIGHT cases legitimately have21 phases."""
    for key,expected in {'state':'closed','pending':0,'queued':[],'running':None,'worker_pid':None,
                         'worker_alive':False,'dispatcher_alive':False}.items():exact(value[key],expected,'Close did not release '+key)
    require(type(value['last_submitted_id']) is int and value['last_submitted_id']>=0,'Invalid closed submission count')
    ids=[]
    for job in value['jobs']:
        require(type(job['job_id']) is int and 0<job['job_id']<=value['last_submitted_id'],'Invalid terminal job identity')
        ids.append(job['job_id']);require(job['state'] in ('returned','failed','cancelled') and job['reaped'] is True,'Closed job not terminal/reaped')
        stamps=[job[k] for k in ('submitted_at','started_at','finished_at') if job[k] is not None]
        require(job['submitted_at'] is not None and job['finished_at'] is not None and all(finite(x) and interval['started']<=x<=interval['finished'] for x in stamps) and stamps==sorted(stamps),'Terminal clocks contradict actual capture')
        if job['pid'] is None:require(job['started_at'] is None and job['exitcode'] is None,'Unspawned job has process fields')
        else:require(type(job['pid']) is int and job['pid']>0 and type(job['exitcode']) is int,'Terminal process identity/exit missing')
        if job['state']=='returned':require(type(job['pid']) is int and type(job['exitcode']) is int and job['exitcode']==0,'Returned worker did not exit0')
    require(ids==sorted(set(ids)),'Closed job IDs repeat or reorder')

def _reference_rows(root):
    rows={row['definition']['id']:row for row in load(root/'references/e09-coverage-validation.json')['cases']}
    fingerprints=expectations(root);selected={}
    for identifier in EXPECTED_IDS:
        row=rows[identifier];raw=raw64(row['requestBytesBase64']);request=embedded_json(raw);request['_sha']=digest(raw)
        observation=decode_capture(row['captures'][0])
        require(semantic(observation,request)==fingerprints[identifier],'Original fixed E09 reference facts differ')
        selected[identifier]=(row['definition'],raw,observation)
    return selected

def _error(actual):
    expected={'type':'ResourceClosedError','code':'RESOURCE_CLOSED','path':'','message':'The native instance is closed',
              'string':'RESOURCE_CLOSED at /: The native instance is closed'}
    exact(actual,expected,'Closed public API error differs')

def _validate_cell(value,root):
    require(value['schema']=='py-elk-e10-platform-cell/v1','Unknown platform cell schema')
    require(value['os'] in ('Windows','Linux') and value['pythonMinor'] in MINORS,'Unknown platform cell')
    exact(value['fullValidation'],False,'Platform probe must not claim full validation')
    source=path(value['actualSourceRoot']);python=path(value['candidatePython']);wheel=path(value['wheel'])
    command=check_command(value);cwd=path(command['cwd'])
    require(not cwd.is_relative_to(source),'Platform command ran inside checkout')
    expected=[str(python),'-I',str(source/COLLECTOR),'--wheel',str(wheel),'--suite',str(source/SUITE),'--out',command['argv'][-1]]
    exact(command['argv'],expected,'Actual isolated platform command role differs')
    require(path(command['argv'][-1]).is_relative_to(cwd),'Platform observation output is outside recorded working directory')
    exact(command['environmentPolicy'],{'pathEmpty':True,'overridesAbsent':True},'Actual runtime environment policy differs')
    raw=raw64(value['observationBytesBase64']);require(digest(raw)==value['observationSha256'],'Original platform observation bytes differ')
    observation=embedded_json(raw);require(observation['schema']=='py-elk-e10-platform-observation/v1','Unknown platform observation schema')
    exact(observation['fullValidation'],False,'Observation claims full validation')
    exact(observation['executionDependencies'],execution_dependencies(root),'Capture dependency/request identity changed; old raw must not be rebound')
    engine=observation['engine'];version=engine['versionInfo'];installed=observation['installed']
    require(type(version) is list and len(version)==3 and all(type(v) is int and v>=0 for v in version) and
            str(version[0])+'.'+str(version[1])==value['pythonMinor'] and engine['implementation']=='cpython','Actual CPython minor does not match matrix cell')
    actual_version=re.match(r'^(\d+)\.(\d+)\.(\d+)(?:\D|$)',engine['python'])
    require(actual_version is not None and list(map(int,actual_version.groups()))==version,'Actual sys.version contradicts recorded versionInfo')
    require(engine['name']=='pyelk' and engine['version']==installed['version'] and engine['python']==installed['python'] and
            engine['platform']['system']==value['os'] and path(engine['executable'])==python,'Actual engine/platform/interpreter differs')
    require(all(type(engine['platform'][k]) is str and bool(engine['platform'][k]) for k in ('system','release','version','machine')),'Actual platform identity incomplete')
    windows=value['os']=='Windows'
    require(all(isinstance(item,PureWindowsPath)==windows for item in (source,python,wheel,cwd)),
            'Actual OS contradicts historical runtime path style')
    require(engine['isolated'] is True and engine['pathEmpty'] is True and engine['overridesAbsent'] is True,'Actual isolated environment differs')
    for key in ('executableSha256','baseExecutableSha256'):require(re.fullmatch(r'[0-9a-f]{64}',engine[key]) is not None,'Interpreter executable digest missing')
    prefix,base=path(engine['prefix']),path(engine['basePrefix']);path(engine['baseExecutable'])
    require(prefix!=base and python.is_relative_to(prefix) and path(installed['modulePath']).is_relative_to(prefix),'Actual fresh venv/imported package identity differs')
    installation_source(value,engine,source)
    validate_process_identity(engine,{'executionPid':command['pid']},value['launcherPid'])
    require(value['wheelSha256']==installed['wheelSha256'] and re.fullmatch(r'[0-9a-f]{64}',value['wheelSha256']) is not None,'Cell/wheel identity differs')
    validate_installed_identity(installed,root,actual_source_root=value['actualSourceRoot'])
    interval=observation['captureInterval'];require(interval['clock']=='time.monotonic' and
        all(finite(interval[k]) for k in ('started','finished')) and 0<=interval['started']<interval['finished'],'Invalid capture interval')
    definitions=load(root/SUITE/'cases.json');references=_reference_rows(root)
    require(len(observation['cases'])==6,'Platform six-case denominator differs');reports=[]
    for row,definition in zip(observation['cases'],definitions['cases']):
        exact(row['definition'],definition,'Platform case definition differs');require(row['id']==definition['id'],'Platform case identity/order differs')
        request_raw=raw64(row['requestBytesBase64']);expected_raw=(root/SUITE/definition['request']).read_bytes()
        require(request_raw==expected_raw and digest(request_raw)==definition['requestSha256']==row['requestSha256'],'Original platform request bytes differ')
        exact(row['request'],embedded_json(request_raw),'Original platform parsed request differs')
        old_definition,old_raw,reference=references[definition['referenceCase']]
        require(old_raw==request_raw,'Platform reference is not the same original request')
        observed=row['observation'];exact(observed['engine'],engine,'Per-case actual interpreter identity differs')
        report=compare_case(old_definition,request_raw,reference,observed);reports.append({'id':row['id'],'passed':report['passed'],'rawStrictPassed':report['rawStrictPassed']})
        processors=[]
        if definition['expectedOutcome']=='returned' and row['request']['graph'].get('children'):
            processors=list(NATIVE_PROCESSORS)
            if old_definition['geometry']['direction']!='RIGHT':processors=['GraphTransformer:PRE',*processors,'GraphTransformer:POST']
        exact(observed['traceSummary'],{'phaseCount':len(processors),'processors':processors,'outcomes':['returned']*len(processors)},'Actual representative phase sequence differs')
        closed_snapshot(observed['closedSnapshot'],interval)
    metadata=observation['metadata'];exact(metadata['queries'],native_metadata_contract(root)['default'],'Actual metadata capabilities differ')
    require(set(metadata['closedQueryErrors'])=={'knownLayoutAlgorithms','knownLayoutOptions','knownLayoutCategories'},'Closed metadata query denominator differs')
    for error in metadata['closedQueryErrors'].values():_error(error)
    _error(metadata['closedLayoutError']);closed_snapshot(metadata['closedSnapshot'],interval)
    cancel=observation['cancel'];cpu=load(root/definitions['cancelRequest']['path'])['cpuGraph']
    expected_fingerprint=digest(json.dumps(cpu,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    require(cancel['inputBeforeSha256']==cancel['inputAfterSha256']==expected_fingerprint,'Cancellation original CPU graph changed')
    require(cancel['taskDoneBeforeCancel'] is False and cancel['cancelledErrorType']=='CancelledError','No actual running cancellation')
    events=cancel['phaseEvents'];require(type(events) is list and bool(events),'Actual CPU phase observation missing')
    require(finite(cancel['cancelRequestedAt']) and interval['started']<=cancel['cancelRequestedAt']<=interval['finished'],'Invalid cancellation observation clock')
    for event in events:
        snapshot=event['snapshot'];validate_snapshot(snapshot,interval)
        job=next(j for j in snapshot['jobs'] if j['job_id']==snapshot['running']);progress=job['progress']
        require(finite(event['observedAt']) and interval['started']<=event['observedAt']<=cancel['cancelRequestedAt'] and
                snapshot['worker_alive'] is True and progress is not None and progress['index']>=1 and progress['previous_outcome']=='returned' and
                progress['process_time']>0 and job['pid']==cancel['pidBeforeCancel']['pid'],'Cancellation did not observe real running CPU/worker')
    for name,alive in (('pidBeforeCancel',True),('pidAfterCancel',False)):
        record=cancel[name]
        require(record['method']==('OpenProcess/GetExitCodeProcess' if windows else 'kill(pid,0)'),
                'Actual OS contradicts original native PID observation method')
        if record['method']=='OpenProcess/GetExitCodeProcess':require(type(record['opened']) is bool,'OS PID opened flag is not boolean')
        _os_pid(record,alive)
    require(cancel['pidBeforeCancel']['pid']==cancel['pidAfterCancel']['pid'],'Cancellation PID changed')
    for name in ('afterCancel','afterRecovery','closedSnapshot'):validate_snapshot(cancel[name],interval)
    cancelled=cancel['afterCancel'];require(cancelled['pending']==0 and cancelled['dispatcher_alive'] is False and
        any(j['pid']==cancel['pidAfterCancel']['pid'] and j['state']=='cancelled' and j['reaped'] is True for j in cancelled['jobs']),'Cancelled worker resources not reaped')
    chain=next(c for c in definitions['cases'] if c['id']=='layered-chain');require(cancel['recoveryRequestSha256']==chain['requestSha256'],'Cancellation recovery request differs')
    definition,request_raw,reference=references['layered-chain'];request=embedded_json(request_raw)
    require(geometry(request,{'outcome':'returned','result':cancel['recoveryResult']},definition['geometry'])['passed'],'Real cancellation recovery geometry failed')
    require([x['processor'] for x in cancel['recoveryTrace']]==list(NATIVE_PROCESSORS) and all(x['outcome']=='returned' for x in cancel['recoveryTrace']),'Cancellation recovery did not execute real phases')
    require(cancel['afterRecovery']['pending']==0 and cancel['afterRecovery']['dispatcher_alive'] is False,'Recovery left active resources')
    closed_snapshot(cancel['closedSnapshot'],interval)
    return {'passed':True,'errors':[],'id':value['id'],'os':value['os'],'pythonMinor':value['pythonMinor'],
        'artifactKind':value['installation']['artifactKind'],'installationSourceValidated':True,
        'caseCount':6,'cases':reports,'metadataValidated':True,'realRunningCancellationValidated':True,
        'wheelSha256':installed['wheelSha256'],'fullValidation':False,'historicalExecutionAuthenticated':False}

def validate_cell(value,root=ROOT):
    try:return _validate_cell(value,Path(root))
    except (ValueError,KeyError,TypeError,AttributeError,OSError,IndexError,OverflowError,StopIteration) as error:
        return {'passed':False,'errors':[str(error)],'fullValidation':False,'historicalExecutionAuthenticated':False}

def validate_matrix(cells,root=ROOT):
    expected={(os,minor) for os in ('Windows','Linux') for minor in MINORS};results=[validate_cell(c,root) for c in cells]
    actual=[(r.get('os'),r.get('pythonMinor')) for r in results];errors=[]
    if len(cells)!=8 or len(set(actual))!=8 or set(actual)!=expected:errors.append('Exactly eight distinct Windows/Linux CPython3.11-3.14 wheel cells required')
    if not all(r['passed'] for r in results):errors.append('One or more actual platform cells failed verification')
    if any(r.get('artifactKind')!='wheel' for r in results):errors.append('Eight wheel cells cannot be substituted by source-install representatives')
    if len({r.get('wheelSha256') for r in results})!=1:errors.append('Platform cells use different wheel bytes')
    return {'passed':not errors,'errors':errors,'expectedCells':8,'measuredPassedCells':sum(r['passed'] for r in results),
        'cells':results,'fullValidation':False,'historicalExecutionAuthenticated':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('receipt',type=Path);parser.add_argument('--matrix',action='store_true');parser.add_argument('--out',type=Path)
    args=parser.parse_args();value=load(args.receipt)
    if args.matrix:
        entries=value if type(value) is list else value['cells']
        result=validate_matrix([load(contained(ROOT,item)) if type(item) is str else item for item in entries])
    else:result=validate_cell(value)
    result.update(receiptSha256=sha256(args.receipt),verifierSha256=sha256(Path(__file__)),
        verifierSourcesSha256={p.relative_to(ROOT).as_posix():sha256(p) for p in sorted((ROOT/'scripts').rglob('*.py'))})
    if args.out:
        from layout_checks import write
        write(args.out,result)
    print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
