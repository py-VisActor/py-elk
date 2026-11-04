"""Independent E09 diagnostics coverage and portable installed receipts.

Only actual monitor executionTime leaves receive the explicit E09 comparison
view. Raw strict results and original bytes remain available. The old profiles,
coordinate tolerances, and business fields are never changed by this module.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import copy
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath, PurePosixPath
import shutil
import struct
import subprocess
import sys
import time

# Trusted development tooling only; never make the source package importable.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from layout_checks import ROOT, load, sha256, write, diff, contract, compare_observations, geometry, input_preservation
from validate_layout import run
from validate_e04_runtime import embedded_json, exact
from build_e09_suite import SUITE, check as check_suite, math_request, encoded

COLLECTOR='tools/reference/capture_e09_layout.cjs'
SCRIPT='scripts/validate_e09_coverage.py'
RECORD='references/e09-coverage-validation.json'
EXPECTATIONS=SUITE+'/reference-expectations.json'
# Frozen from independent, original Node observations, before candidate capture.
# This is a semantic fingerprint, not a digest of mutable Python progress.
EXPECTATIONS_SHA='5096d71e5b7ed0ef6b950442c245a1ccd656fd1d2cbea26f6546c74caddcfce3'
HOST_REQUEST=SUITE+'/host-checks.json'
NUMERIC_REFERENCE=SUITE+'/numeric-reference.json'
NUMERIC_REFERENCE_SHA='021a135ef9e81c3679fb182511c72ef5fe1a384dfc230dd426faecd0a9ac2fbc'
OVERRIDES=('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME')
NEGATIVE={
 'error-unknown-endpoint':('ModelValidationError','UNKNOWN_ENDPOINT','/edges/0/targets/0','Referenced node or port does not exist'),
 'error-unknown-algorithm':('UnknownAlgorithmError','UNKNOWN_ALGORITHM','/local/elk.algorithm','Unknown algorithm identifier: does-not-exist'),
 'error-missing-graph':('ModelValidationError','INVALID_GRAPH','','Graph root must be a mapping')}
REFERENCE_ERRORS={
 'error-unknown-endpoint':"org.eclipse.elk.graph.json.JsonImportException: Referenced shape does not exist: missing",
 'error-unknown-algorithm':"org.eclipse.elk.core.UnsupportedConfigurationException: Layout algorithm 'does-not-exist' not found for Root Node root",
 'error-missing-graph':"Missing mandatory parameter 'graph'."}

def require(condition,message):
    if not condition:raise ValueError(message)

def digest(raw):return hashlib.sha256(raw).hexdigest()
def b64(raw):return base64.b64encode(raw).decode('ascii')
def unb64(value):return base64.b64decode(value,validate=True)
def finite(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except (OverflowError,ValueError):return False
def historical_path(value):return PureWindowsPath(value) if '\\' in value else PurePosixPath(value)
def absolute_path(value):
    require(type(value) is str and bool(value),'Historical path must be a nonempty string')
    path=historical_path(value)
    require(path.is_absolute() and '..' not in path.parts,'Historical path must be absolute without parent traversal')
    return path
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()

def installed_package(pyelk):
    import importlib.metadata
    package=Path(pyelk.__file__).resolve().parent
    distribution=importlib.metadata.distribution('py-elk')
    require(not package.is_relative_to(ROOT/'src') and
            (package/'__init__.py')==Path(distribution.locate_file('pyelk/__init__.py')).resolve(),
            'Capture must import the actual installed distribution outside the source tree')
    return package
def baseline(root=ROOT):
    lock=load(Path(root)/'UPSTREAM.json')
    return {'javascript':{k:lock['javascript'][k] for k in ('version','commit')},
            'distribution':copy.deepcopy(lock['distribution'])}
def sources(root=ROOT):
    names=(SCRIPT,'scripts/build_e09_suite.py','scripts/layout_checks.py','scripts/e07_geometry_premise.py','scripts/e09_geometry_premise.py',
           'scripts/verify_installed_wheel.py','scripts/validate_layout.py','scripts/validate_e04_runtime.py',
           'scripts/validate_e07_runtime.py','scripts/validate_e06_runtime.py','scripts/validate_e08_api.py',
           'scripts/source_read_cache.py','references/native-contract.json',
           'docs/decisions/0008-e09-diagnostics-coverage.md','references/e09-geometry-premise.json',
           'references/e09-metadata-schema.json','tools/reference/e09_host_lifecycle_probe.py')
    return {name:sha256(Path(root)/name) for name in names}

def run_candidate(argv,folder,env,timeout=120):
    """Actual Popen PID is part of this protocol, unlike legacy run receipts."""
    start=time.monotonic();process=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    timed_out=False
    try:stdout,stderr=process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out=True;process.kill();stdout,stderr=process.communicate()
    (folder/'stdout.log').write_bytes(stdout);(folder/'stderr.log').write_bytes(stderr)
    record={'argv':argv,'cwd':str(ROOT),'exitCode':process.returncode,'timedOut':timed_out,
        'executionPid':process.pid,'elapsedSeconds':time.monotonic()-start,'stdoutSha256':digest(stdout),'stderrSha256':digest(stderr)}
    write(folder/'command.json',record);return record

def validate_process_identity(engine,command,launcher_pid):
    """Direct Python child or one real Windows venv redirector, never self.

    These are finite receipt consistency rules, not historical authentication.
    Actual capture records come from Popen.pid and the child's os.getpid/ppid.
    """
    require(type(launcher_pid) is int and launcher_pid>0,'Invalid actual launcher PID')
    pid,parent_pid,execution_pid=engine['pid'],engine['parentPid'],command['executionPid']
    require(all(type(x) is int and x>0 for x in (pid,parent_pid,execution_pid)),
            'Actual process identities must be positive integers')
    require(pid!=launcher_pid and parent_pid!=pid and execution_pid!=launcher_pid,
            'Actual launcher, child and parent process identities contradict')
    direct=execution_pid==pid and parent_pid==launcher_pid
    redirector=execution_pid==parent_pid and execution_pid not in (launcher_pid,pid)
    require(direct or redirector,'Actual Popen/engine relationship is neither direct nor one-level redirector')
def suite(root=ROOT):
    check_suite(root)
    return load(Path(root)/SUITE/'cases.json')
def flags(request):
    args=request['layoutArguments'];values=tuple(args.get(k,False) for k in ('logging','measureExecutionTime'))
    require(all(type(v) is bool for v in values),'Diagnostics flags must be exact booleans')
    return values

def monitor_view(tree,logging,measured,clock=None,path='/result/logging'):
    """Validate only the actual generated monitor tree; return time-free view."""
    require(type(tree) is dict and set(tree)<= {'name','logs','executionTime','children'} and
            type(tree.get('name')) is str and bool(tree['name']),'Malformed generated monitor at '+path)
    result=copy.deepcopy(tree)
    if logging:
        if 'logs' in tree:require(type(tree['logs']) is list and bool(tree['logs']) and all(type(x) is str for x in tree['logs']),'Malformed monitor logs')
    else:require('logs' not in tree,'Unexpected generated logs when logging is false')
    if measured:
        require('executionTime' in tree and finite(tree['executionTime']),'Missing or nonfinite generated executionTime')
        elapsed=tree['executionTime']
        try:
            ticks=round(elapsed/0.000001)
            scaled=float(ticks*1000)*1e-9
        except (OverflowError,ValueError):raise ValueError('Generated executionTime exceeds representable millisecond scaling') from None
        require(scaled==elapsed,'Generated executionTime does not use fixed millisecond scaling')
        if clock is not None:
            # This is a normal observed interval check, not a source guarantee
            # that Date.now cannot move backwards. Pure views allow negatives.
            span=clock['endMs']-clock['startMs']
            require(span>=0 and 0<=ticks<=span,'Generated clock lies outside actual normal capture interval')
        result['executionTime']=0
    else:require('executionTime' not in tree,'Unexpected generated executionTime when measurement is false')
    if 'children' in tree:
        require(type(tree['children']) is list and bool(tree['children']),'Empty or invalid monitor children')
        result['children']=[monitor_view(x,logging,measured,clock,path+'/children/'+str(i)) for i,x in enumerate(tree['children'])]
    return result

def observation_view(observation,request,*,reference,check_clock=True):
    contract(observation)
    require(observation['requestSha256']==request['_sha'],'Original request SHA differs')
    clock=observation['clock']
    require(set(clock)=={'startMs','endMs'} and all(type(x) is int and abs(x)<=2**53-1 for x in clock.values()),'Actual safe integer wall-clock interval missing')
    require(clock['endMs']>=clock['startMs'],'Normal captured wall interval moved backwards; retain as nonqualifying evidence')
    for before,key in (('inputBefore','graph'),('constructorBefore','constructor'),('argumentsBefore','layoutArguments')):
        exact(observation[before],request[key],'Original before observation differs')
    for after,key in (('constructorAfter','constructor'),('argumentsAfter','layoutArguments')):
        exact(observation[after],request[key],'Call input mutated')
    result=copy.deepcopy(observation);logging,measured=flags(request)
    if observation['outcome']=='returned':
        require(type(observation['result']) is dict,'Successful result must be a graph')
        if logging or measured:
            tree=observation['result'].get('logging')
            require(type(tree) is dict and tree.get('name')=='Recursive Graph Layout','Generated root monitor missing or renamed')
            result['result']['logging']=monitor_view(tree,logging,measured,clock if check_clock else None)
            if reference:
                exact(observation['inputAfter'],observation['result'],'Reference successful graph mutation differs from returned graph')
                result['inputAfter']['logging']=copy.deepcopy(result['result']['logging'])
        else:require('logging' not in observation['result'],'Reserved root logging was not cleaned')
        if reference:exact(observation['inputAfter'],observation['result'],'Reference successful graph mutation differs')
    if not reference:
        exact(observation['inputAfter'],request['graph'],'Native caller graph mutated')
        exact(observation['termination'],{'outcome':'returned'},'Native real termination failed')
    return result

def semantic(observation,request):
    return digest(canonical(contract(observation_view(observation,request,reference=True))))

def expectations(root=ROOT):
    require(EXPECTATIONS_SHA is not None,'Independent reference semantics have not been frozen')
    path=Path(root)/EXPECTATIONS
    require(sha256(path)==EXPECTATIONS_SHA,'Independent fixed reference semantics differ')
    value=load(path)
    require(value['schema']=='py-elk-e09-reference-semantics/v1','Unknown reference semantics schema')
    return value['cases']

def numeric_reference(root=ROOT):
    path=Path(root)/NUMERIC_REFERENCE
    require(sha256(path)==NUMERIC_REFERENCE_SHA,'Independent intrinsic Number oracle bytes differ')
    value=load(path);request=embedded_json(unb64(value['requestBytesBase64']))
    require(len(request['entries'])==298 and len(value['captures'])==3,'Number oracle denominator differs')
    rows=[];pids=[]
    for ordinal,capture in enumerate(value['captures']):
        require(capture['repetition']==ordinal,'Number oracle repetition differs')
        observation=decode_capture(capture);pids.append(observation['engine']['pid'])
        require(observation['requestSha256']==digest(unb64(value['requestBytesBase64'])),'Number oracle original request differs')
        exact(observation['baseline']['filesSha256'],baseline(root)['distribution']['sha256Files'],'Number oracle pinned npm differs')
        require(len(observation['entries'])==298,'Number oracle entry denominator differs')
        for expected,entry in zip(request['entries'],observation['entries']):
            require(entry['id']==expected['id'] and entry['bitsHex']==expected['bitsHex'],'Number oracle original bits differ')
            bits=struct.pack('>d',float(entry['string'])).hex()
            require(bits==entry['roundTripBitsHex'],'Number intrinsic round-trip bytes differ')
            require(bits==entry['bitsHex'] or entry['bitsHex']=='8000000000000000' and bits=='0000000000000000','Number oracle lost an unexpected bit')
        rows.append(observation['entries'])
    exact(rows[0],rows[1],'Independent Number oracle observations differ');exact(rows[0],rows[2],'Independent Number oracle observations differ')
    require(len(set(pids))==3,'Independent Number oracle PID reused')
    return rows[0]

def logs_of(observation):
    found=[]
    def visit(tree):
        found.extend(tree.get('logs',[]))
        for child in tree.get('children',[]):visit(child)
    tree=observation.get('result',{}).get('logging')
    if type(tree) is dict and tree.get('name')=='Recursive Graph Layout':visit(tree)
    return found

def measured_values(observation):
    tree=observation.get('result',{}).get('logging');found=[]
    def visit(node):
        if 'executionTime' in node:found.append(node['executionTime'])
        for child in node.get('children',[]):visit(child)
    if type(tree) is dict and tree.get('name')=='Recursive Graph Layout':visit(tree)
    return found

def command_blob(folder,command):
    return {'command':command,**{s+'BytesBase64':b64((folder/(s+'.log')).read_bytes()) for s in ('stdout','stderr')}}

def validate_command(value,argv,cwd):
    command=value['command'];exact(command['argv'],argv,'Actual execution argv differs')
    require(command['cwd']==str(cwd) and type(command['exitCode']) is int and command['exitCode']==0 and command['timedOut'] is False,'Actual process failed or working directory differs')
    require(finite(command['elapsedSeconds']) and command['elapsedSeconds']>=0,'Invalid actual command duration')
    for stream in ('stdout','stderr'):
        require(digest(unb64(value[stream+'BytesBase64']))==command[stream+'Sha256'],'Actual command log bytes differ')

def decode_capture(capture):
    raw=unb64(capture['observationBytesBase64'])
    require(digest(raw)==capture['observationSha256'],'Actual observation SHA differs')
    return embedded_json(raw)

def verify_reference(value,root=ROOT,*,provisional=False):
    root=Path(root);definitions=suite(root);source=historical_path(value['actualSourceRoot']);origin=historical_path(value['actualExecutionRoot'])
    require(value['schema']=='py-elk-e09-reference-receipt/v1','Unknown E09 reference schema')
    exact(value['baseline'],baseline(root),'Fixed npm identity differs')
    require(value['collectorSha256']==sha256(root/COLLECTOR),'Reference collector bytes differ')
    require(type(value['repeat']) is int and value['repeat']>=(1 if provisional else 3),'Reference repetition denominator differs')
    require(len(value['cases'])==definitions['caseCount'],'Reference case denominator differs')
    frozen=None if provisional else expectations(root)
    rows=[];all_logs=[];timed_cases=0;nonzero=0
    for actual,definition in zip(value['cases'],definitions['cases']):
        exact(actual['definition'],definition,'Reference per-case definition differs')
        raw=unb64(actual['requestBytesBase64']);require(raw==(root/SUITE/definition['request']).read_bytes(),'Original reference request differs')
        request=embedded_json(raw);request['_sha']=digest(raw)
        require(len(actual['captures'])==value['repeat'],'Reference repetitions missing')
        hashes=[];pids=[]
        for ordinal,capture in enumerate(actual['captures']):
            require(type(capture['repetition']) is int and capture['repetition']==ordinal,'Reference repeat slot differs')
            folder=origin/definition['id']/('repeat-'+str(ordinal))
            argv=[value['node'],str(source/COLLECTOR),value['package'],str(origin/definition['id']/'request.json'),str(folder/'observation.json')]
            validate_command(capture,argv,source)
            observation=decode_capture(capture);engine=observation['engine']
            require(type(engine['pid']) is int and engine['pid']>0,'Actual reference process PID missing')
            pids.append(engine['pid'])
            require(engine['name']=='elkjs' and engine['version']=='0.12.1' and engine['entrypoint']=='lib/elk.bundled.js' and
                    engine['entrypointSha256']==value['baseline']['distribution']['sha256Files']['lib/elk.bundled.js'] and
                    engine['executable']==value['node'] and engine['executableSha256']==value['nodeSha256'] and engine['node']==value['nodeVersion'],'Actual reference engine identity differs')
            require(observation['outcome']==definition['expectedOutcome'],'Reference outcome differs')
            if observation['outcome']=='threw':exact(observation['error'],{'name':'Error','message':REFERENCE_ERRORS[definition['masterId']]},'Original named reference error differs')
            else:
                report=geometry(math_request(request),observation,definition['geometry'])
                require(report['passed'],'Original reference geometry failed: '+definition['id']+' '+str(report))
            h=semantic(observation,request);hashes.append(h);all_logs.extend(logs_of(observation))
            values=measured_values(observation);timed_cases+=bool(values);nonzero+=sum(x!=0 for x in values)
            if frozen is not None:require(h==frozen[definition['id']],'Fixed original reference semantics differ: '+definition['id'])
        require(len(set(hashes))==1,'Reference source-generated-time view is nondeterministic')
        require(len(set(pids))==value['repeat'],'Reference process PID reused across independent repetitions')
        rows.append({'id':definition['id'],'semanticSha256':hashes[0]})
    require(nonzero>0,'No nonzero real reference wall measurement was observed')
    return {'passed':True,'caseCount':len(rows),'masterCount':25,'repeat':value['repeat'],'semantics':rows,
            'timedCaseCaptureCount':timed_cases,'nonzeroMeasuredLeafCount':nonzero,
            'bkNonemptyMarkedWitness':any(x.startswith('Marked edges: [') and x!='Marked edges: []' for x in all_logs),
            'bkInfeasibleWitness':any('breaks on' in x for x in all_logs)}

def capture_reference(out,package,node='node',repeat=3):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);package=Path(package).resolve()
    node=str(Path(shutil.which(node) or node).resolve());definitions=suite();cases=[]
    collector_start=sha256(ROOT/COLLECTOR);baseline_start=baseline()
    env=os.environ.copy()
    for key in list(env):
        if key.upper() in OVERRIDES:env.pop(key)
    for definition in definitions['cases']:
        parent=out/definition['id'];parent.mkdir();raw=(ROOT/SUITE/definition['request']).read_bytes();(parent/'request.json').write_bytes(raw);captures=[]
        for ordinal in range(repeat):
            folder=parent/('repeat-'+str(ordinal));folder.mkdir()
            cmd=run([node,str(ROOT/COLLECTOR),str(package),str(parent/'request.json'),str(folder/'observation.json')],folder,120,env=env)
            require(cmd['exitCode']==0 and cmd['timedOut'] is False,'Reference process failed: '+definition['id'])
            captures.append({'repetition':ordinal,**command_blob(folder,cmd),'observationBytesBase64':b64((folder/'observation.json').read_bytes()),'observationSha256':sha256(folder/'observation.json')})
        cases.append({'definition':definition,'requestBytesBase64':b64(raw),'captures':captures})
    require(sha256(ROOT/COLLECTOR)==collector_start,'Reference collector changed during real capture')
    exact(baseline(),baseline_start,'Fixed npm identity changed during real capture')
    first=decode_capture(cases[0]['captures'][0]);value={'schema':'py-elk-e09-reference-receipt/v1','repeat':repeat,
        'actualSourceRoot':str(ROOT),'actualExecutionRoot':str(out),'node':node,'nodeSha256':sha256(Path(node)),
        'nodeVersion':first['engine']['node'],'package':str(package),'baseline':baseline_start,'collectorSha256':collector_start,'cases':cases}
    write(out/'receipt.json',value)
    result=verify_reference(value,provisional=EXPECTATIONS_SHA is None);write(out/'report.json',result);return result

async def candidate_capture(request_path,output):
    # Imports occur only in the explicitly isolated installed subprocess.
    import pyelk
    from pyelk import ELK
    require(bool(sys.flags.isolated) and os.environ.get('PATH')=='' and not any(k.upper() in OVERRIDES for k in os.environ),
            'Candidate capture requires -I, empty PATH and no engine/interpreter overrides')
    raw=Path(request_path).read_bytes();request=embedded_json(raw)
    graph=copy.deepcopy(request['graph']);constructor=copy.deepcopy(request['constructor']);args=copy.deepcopy(request['layoutArguments'])
    package=installed_package(pyelk)
    observation={'schema':'py-elk-layout-observation/v1','requestSha256':digest(raw),
        'engine':{'name':'pyelk','version':pyelk.__version__,'modulePath':str(package),'python':sys.version,
            'executable':sys.executable,'isolated':bool(sys.flags.isolated),'pid':os.getpid(),'parentPid':os.getppid(),
            'pathEmpty':os.environ.get('PATH')=='','overridesAbsent':not any(k.upper() in OVERRIDES for k in os.environ),
            'sourceSha256':{p.relative_to(package).as_posix():sha256(p) for p in sorted(package.rglob('*.py'))}},
        'inputBefore':copy.deepcopy(graph),'constructorBefore':copy.deepcopy(constructor),'argumentsBefore':copy.deepcopy(args),
        'clock':{'startMs':time.time_ns()//1_000_000}}
    elk=None
    try:
        elk=ELK(constructor);observation['result']=await elk.layout(graph,args);observation['outcome']='returned'
    except Exception as error:
        observation.update(outcome='threw',error={'name':type(error).__name__,'message':str(error)},
            errorDetails={key:getattr(error,key,None) for key in ('code','path','message')})
    observation['clock']['endMs']=time.time_ns()//1_000_000
    observation.update(inputAfter=graph,constructorAfter=constructor,argumentsAfter=args)
    if elk is not None:elk.terminateWorker();observation['termination']={'outcome':'returned'}
    else:observation['termination']={'outcome':'notConstructed'}
    with Path(output).open('x',encoding='utf8',newline='\n') as stream:json.dump(observation,stream,ensure_ascii=False,allow_nan=False,indent=2);stream.write('\n')

async def host_capture(request_path,output):
    """Installed host probes; controlled primitive/kernel instruments are named."""
    import itertools
    from unittest.mock import patch
    import pyelk
    from pyelk import ELK
    from pyelk.execution.diagnostics import BasicProgressMonitor, number_text
    from pyelk.execution.context import create_context
    from pyelk.algorithms.layered.pipeline import layout_context
    from pyelk.algorithms.layered import import_export, pipeline
    require(bool(sys.flags.isolated) and os.environ.get('PATH')=='' and not any(k.upper() in OVERRIDES for k in os.environ),'Host capture must use isolated clean installed interpreter')
    raw=Path(request_path).read_bytes();request=embedded_json(raw);package=installed_package(pyelk)
    value={'schema':'py-elk-e09-host-observation/v1','requestSha256':digest(raw),
        'engine':{'name':'pyelk','version':pyelk.__version__,'modulePath':str(package),'python':sys.version,'executable':sys.executable,
          'isolated':bool(sys.flags.isolated),'pid':os.getpid(),'parentPid':os.getppid(),'pathEmpty':os.environ.get('PATH')=='',
          'overridesAbsent':not any(k.upper() in OVERRIDES for k in os.environ),
          'sourceSha256':{p.relative_to(package).as_posix():sha256(p) for p in sorted(package.rglob('*.py'))}},
        'publicCases':[],'clockMode':'controlled primitive ticks are not real layout timing'}
    for definition in request['publicCases']:
        original=definition['request'];graph=copy.deepcopy(original['graph']);constructor=copy.deepcopy(original['constructor']);arguments=copy.deepcopy(original['layoutArguments'])
        item={'id':definition['id'],'inputBefore':copy.deepcopy(graph),'constructorBefore':copy.deepcopy(constructor),'argumentsBefore':copy.deepcopy(arguments)}
        elk=ELK(constructor)
        try:item.update(outcome='returned',result=await elk.layout(graph,arguments))
        except Exception as error:item.update(outcome='threw',error={'name':type(error).__name__,**{k:getattr(error,k,None) for k in ('code','path','message')}})
        finally:elk.terminateWorker()
        item.update(inputAfter=graph,constructorAfter=constructor,argumentsAfter=arguments,termination={'outcome':'returned'})
        value['publicCases'].append(item)
    primitives={'clocks':[]}
    for start,end in ((1000,1002),(1000,1000),(2002,2000),(1000,1007)):
        ticks=iter((start,end));reads=[]
        def clock():
            tick=next(ticks);reads.append(tick);return tick
        monitor=BasicProgressMonitor(measure_execution_time=True,clock_ms=clock)
        begin=monitor.begin('clock',1);monitor.done()
        primitives['clocks'].append({'ticks':reads,'begin':begin,'tree':monitor.collect()})
    with patch('pyelk.execution.diagnostics.time.time_ns',side_effect=(1000999999,1002000000)) as default_clock:
        monitor=BasicProgressMonitor(measure_execution_time=True);monitor.begin('default',1);monitor.done()
        primitives['defaultClock']={'timeNs':[1000999999,1002000000],'reads':default_clock.call_count,'tree':monitor.collect()}
    primitives['disabledClocks']=[]
    for logging in (False,True):
        reads=[]
        def forbidden():reads.append('unexpected');raise RuntimeError('disabled clock read')
        monitor=BasicProgressMonitor(logging=logging,clock_ms=forbidden);monitor.begin('root',1)
        child=monitor.sub_task(1);child.begin('child',1);child.log('actual message');child.done();monitor.done()
        primitives['disabledClocks'].append({'logging':logging,'reads':reads,'tree':monitor.collect()})
    monitor=BasicProgressMonitor();state={'firstBegin':monitor.begin('original',1),'runningAfterBegin':monitor.is_running()}
    state['repeatBegin']=monitor.begin('other',99);monitor.done();state['runningAfterDone']=monitor.is_running();before=monitor.collect();monitor.done()
    state['repeatDoneBefore']=before;state['repeatDoneAfter']=monitor.collect();state['closedSubTask']=monitor.sub_task(1)
    try:monitor.begin('late',1)
    except Exception as error:state['closedBeginError']={'name':type(error).__name__,'message':str(error)}
    virgin=BasicProgressMonitor()
    try:virgin.done()
    except Exception as error:state['doneBeforeBeginError']={'name':type(error).__name__,'message':str(error)}
    primitives['state']=state
    monitor=BasicProgressMonitor(logging=True);monitor.begin('root',2)
    for name,messages in (('first',('one','two')),('second',())):
        child=monitor.sub_task(1);child.begin(name,1)
        for message in messages:child.log(message)
        child.done()
    monitor.done();before=monitor.collect();mutated=monitor.collect();mutated['children'][0]['logs'].append('caller mutation');mutated['children'].reverse()
    primitives['collect']={'before':before,'mutatedReturn':mutated,'after':monitor.collect()}
    one_ticks,two_ticks=iter((10,12)),iter((20,27));one=BasicProgressMonitor(measure_execution_time=True,clock_ms=lambda:next(one_ticks));two=BasicProgressMonitor(measure_execution_time=True,clock_ms=lambda:next(two_ticks))
    one.begin('one',1);two.begin('two',1);two.done();one.done();primitives['isolation']={'one':one.collect(),'two':two.collect()}
    value['monitorPrimitives']=primitives
    value['numberAdapter']=[{'id':x['id'],'bitsHex':x['bitsHex'],'string':number_text(struct.unpack('>d',bytes.fromhex(x['bitsHex']))[0])} for x in numeric_reference()]
    base=load(ROOT/'tests/fixtures/validation/requests/layered-chain.json');kernel=[]
    for trace_enabled in (False,True):
        ticks=itertools.count(1000);monitor=BasicProgressMonitor(False,True,lambda:next(ticks));events=[];trace=[] if trace_enabled else None
        original_import,original_export=import_export.import_raw_graph,import_export.export_layout
        def imported(*args,**kwargs):
            events.append({'role':'provider-import','rootRunning':monitor.is_running(),'layeredPresent':bool(monitor._children)})
            return original_import(*args,**kwargs)
        def exported(*args,**kwargs):
            events.append({'role':'provider-transfer','rootRunning':monitor.is_running(),'layeredRunning':monitor._children[0].is_running()})
            return original_export(*args,**kwargs)
        with patch.object(import_export,'import_raw_graph',imported),patch.object(import_export,'export_layout',exported),patch.object(pipeline,'snapshot',wraps=pipeline.snapshot) as snapshot:
            context=create_context(base['graph'],constructor=base['constructor'],layout_arguments=base['layoutArguments'])
            result=layout_context(context,trace=trace,monitor=monitor)
        kernel.append({'mode':'kernel-only controlled clock; no ELK lifecycle','traceEnabled':trace_enabled,'events':events,
            'snapshotCalls':snapshot.call_count,'result':result,'tree':monitor.collect(),
            'trace':[] if trace is None else [{'processor':x['processor'],'outcome':x['outcome']} for x in trace]})
    value['kernelBoundaries']=kernel
    with Path(output).open('x',encoding='utf8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,allow_nan=False,indent=2);stream.write('\n')

def validate_host_observation(value,request,root=ROOT):
    require(value['schema']=='py-elk-e09-host-observation/v1','Unknown installed host observation schema')
    exact(value['clockMode'],'controlled primitive ticks are not real layout timing','Controlled clock label differs')
    require(len(value['publicCases'])==len(request['publicCases']),'Public host probe denominator differs')
    for actual,definition in zip(value['publicCases'],request['publicCases']):
        require(actual['id']==definition['id'] and actual['outcome']==definition['expected']['outcome'],'Public host probe slot/outcome differs')
        for suffix in ('Before','After'):
            for stem,key in (('input','graph'),('constructor','constructor'),('arguments','layoutArguments')):
                exact(actual[stem+suffix],definition['request'][key],'Public host probe original inputs differ')
        exact(actual['termination'],{'outcome':'returned'},'Actual public host termination failed')
        if actual['outcome']=='threw':exact(actual['error'],definition['expected']['error'],'Public host rejection class/code/path/message differs: '+definition['id'])
        else:
            observation={'outcome':'returned','result':actual['result']}
            report=geometry(definition['request'],observation,definition['geometry']);require(report['passed'],'Public boundary positive geometry failed')
    p=value['monitorPrimitives'];require(len(p['clocks'])==4,'Controlled primitive clock denominator differs')
    for actual,(start,end) in zip(p['clocks'],((1000,1002),(1000,1000),(2002,2000),(1000,1007))):
        exact(actual,{'ticks':[start,end],'begin':True,'tree':{'name':'clock','executionTime':float((end-start)*1000)*1e-9}},'Controlled primitive tick scale/order differs')
    exact(p['defaultClock'],{'timeNs':[1000999999,1002000000],'reads':2,'tree':{'name':'default','executionTime':float(2000)*1e-9}},'Default integer wall millisecond conversion differs')
    expected_disabled=[]
    for logging in (False,True):
        child={'name':'child'}
        if logging:child['logs']=['actual message']
        expected_disabled.append({'logging':logging,'reads':[],'tree':{'name':'root','children':[child]}})
    exact(p['disabledClocks'],expected_disabled,'Disabled clock read or collect behavior differs')
    exact(p['state'],{'firstBegin':True,'runningAfterBegin':True,'repeatBegin':False,'runningAfterDone':False,
        'repeatDoneBefore':{'name':'original'},'repeatDoneAfter':{'name':'original'},'closedSubTask':None,
        'closedBeginError':{'name':'RuntimeError','message':'The task is already done.'},
        'doneBeforeBeginError':{'name':'RuntimeError','message':'The task has not begun yet.'}},'Source monitor state branches differ')
    expected_collect={'name':'root','children':[{'name':'first','logs':['one','two']},{'name':'second'}]}
    exact(p['collect']['before'],expected_collect,'Monitor collection order differs');exact(p['collect']['after'],expected_collect,'Returned monitor tree aliases private state')
    mutated=copy.deepcopy(expected_collect);mutated['children'][0]['logs'].append('caller mutation');mutated['children'].reverse()
    exact(p['collect']['mutatedReturn'],mutated,'Collection mutation control was not actually applied')
    exact(p['isolation'],{'one':{'name':'one','executionTime':float(2000)*1e-9},'two':{'name':'two','executionTime':float(7000)*1e-9}},'Monitor clocks not isolated')
    exact(value['numberAdapter'],[{k:x[k] for k in ('id','bitsHex','string')} for x in numeric_reference(root)],'Installed Number adapter differs from independent Node intrinsic')
    require(len(value['kernelBoundaries'])==2,'Kernel boundary probe denominator differs')
    base=load(Path(root)/'tests/fixtures/validation/requests/layered-chain.json')
    from build_e09_suite import geometry_policy
    originals={x['definition']['id']:x for x in load(Path(root)/RECORD)['cases']}
    reference_time=decode_capture(originals['layered-chain-flags-01']['captures'][0])['result']['logging']
    reference_logs=decode_capture(originals['layered-chain-flags-10']['captures'][0])['result']['logging']['children'][0]['logs']
    expected_processors=[line.rsplit('.',1)[-1] for line in reference_logs[1:]]
    for index,kernel in enumerate(value['kernelBoundaries']):
        exact(kernel['traceEnabled'],bool(index),'Kernel trace switch differs')
        exact(kernel['mode'],'kernel-only controlled clock; no ELK lifecycle','Kernel instrumentation scope label differs')
        exact(kernel['events'],[{'role':'provider-import','rootRunning':True,'layeredPresent':False},
            {'role':'provider-transfer','rootRunning':True,'layeredRunning':False}],'Actual provider monitor boundaries differ')
        exact(kernel['snapshotCalls'],38 if index else 0,'Tree construction improperly depends on trace snapshots')
        require(geometry(base,{'outcome':'returned','result':kernel['result']},geometry_policy(base))['passed'],'Kernel instrument geometry failed')
        exact(monitor_view(kernel['tree'],False,True),monitor_view(reference_time,False,True),'Kernel instrumentation tree differs from fixed official facts')
        if index:
            exact(kernel['trace'],[{'processor':x,'outcome':'returned'} for x in expected_processors],'Actual traced phase execution differs from fixed source modules')
        else:exact(kernel['trace'],[],'Unexpected trace in uninstrumented branch')
    exact(value['kernelBoundaries'][0]['tree'],value['kernelBoundaries'][1]['tree'],'Trace snapshot work selected a different generated tree/clock')
    exact(value['kernelBoundaries'][0]['result'],value['kernelBoundaries'][1]['result'],'Trace instrumentation changed layout')
    return {'passed':True,'publicCaseCount':len(request['publicCases']),'numberCount':298,'controlledPrimitiveChecks':True,'actualKernelBoundaries':True}

def validate_installed_identity(installed,root=ROOT,*,actual_source_root=None):
    """Check the actual shipped inventory, not development-only source READMEs.

    This is the same package-data policy as the independent runtime audit:
    every Python module, py.typed, and all bundled license/notice materials.
    verify_installed_wheel separately rejects extra files in the installation.
    """
    root=Path(root);package=root/'src/pyelk'
    require(installed['status']=='INSTALLED_WHEEL_BYTES_MATCH' and installed['isolatedInterpreter'] is True,'Installed package identity missing')
    module=absolute_path(installed['modulePath']);source=absolute_path(str(root) if actual_source_root is None else actual_source_root)
    require(not module.is_relative_to(source/'src'),
            'Recorded installation is relative or resolves inside the actual source tree')
    current={p.relative_to(package).as_posix():sha256(p) for p in sorted(package.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and
             (p.suffix=='.py' or p.relative_to(package).parts[0]=='_licenses' or p.name=='py.typed')}
    exact(installed['packageFilesSha256'],current,'Installed shipped package bytes differ from current source')
    from validate_e07_runtime import validate_metadata
    return validate_metadata({'wheelVersion':installed['version'],'distributionMetadata':installed['distributionMetadata']},root)

def compare_case(definition,raw,reference,candidate):
    request=embedded_json(raw);request['_sha']=digest(raw)
    rv=observation_view(reference,request,reference=True);cv=observation_view(candidate,request,reference=False)
    require(candidate['outcome']==definition['expectedOutcome'],'Native outcome differs')
    strict=compare_observations(reference,candidate,profile='strict',request=raw)
    if definition['expectedOutcome']=='threw':
        name,code,path,message=NEGATIVE[definition['masterId']]
        exact(candidate['errorDetails'],{'code':code,'path':path,'message':message},'Explicit native host error fields differ')
        exact(candidate['error'],{'name':name,'message':code+' at '+(path or '/')+': '+message},'Native named error differs')
        return {'id':definition['id'],'passed':True,'classification':'expected-error','rawStrictPassed':strict['passed'],
                'errorPolicy':'explicit Python host categories; original JS names/messages retained, no byte-equality claim'}
    native=compare_observations(rv,cv,profile='native-basic-layered-v1',request=raw)
    require(native['passed'],'E09 source-generated-time comparison differs: '+definition['id']+' '+str(native['publicContract']))
    g=geometry(math_request(request),candidate,definition['geometry']);require(g['passed'],'Native geometry failed: '+definition['id']+' '+str(g))
    return {'id':definition['id'],'passed':True,'classification':'supported','rawStrictPassed':strict['passed'],
            'diagnosticsProfile':'e09-source-generated-monitor-time-v1','generatedTimeLeavesOnly':True,'geometry':g,
            'rawStrict':strict,'comparison':native}

def validate_candidate_receipt(value,root=ROOT):
    root=Path(root);definitions=suite(root);reference=load(root/RECORD)
    verify_reference(reference,root)
    require(value['schema']=='py-elk-e09-installed-coverage/v1','Unknown installed coverage schema')
    require(type(value['repeat']) is int and value['repeat']>=3,'Native independent repetitions below three')
    exact(value['sourceSha256'],sources(root),'Current coverage tooling or ADR bytes differ')
    source=absolute_path(value['actualSourceRoot']);origin=absolute_path(value['actualExecutionRoot'])
    absolute_path(value['candidatePython']);absolute_path(value['wheel'])
    installed=value['installed'];validate_installed_identity(installed,root,actual_source_root=value['actualSourceRoot'])
    exact(embedded_json(unb64(value['installedReceiptBytesBase64'])),installed,'Original installed identity bytes differ')
    validate_command(value['installedCommand'],[value['candidatePython'],'-I',str(source/'scripts/verify_installed_wheel.py'),value['wheel'],'--out',str(origin/'installed-wheel.json')],source)
    require(len(value['cases'])==definitions['caseCount'],'Installed full case denominator differs')
    require(type(value['launcherPid']) is int and value['launcherPid']>0,'Real launcher process identity missing')
    rows=[];timed_cases=0;nonzero=0
    for captured,definition,ref in zip(value['cases'],definitions['cases'],reference['cases']):
        exact(captured['definition'],definition,'Installed per-case definition differs')
        raw=unb64(captured['requestBytesBase64']);require(raw==(root/SUITE/definition['request']).read_bytes(),'Installed original request bytes differ')
        require(len(captured['captures'])==value['repeat'],'Installed per-case repeat denominator differs')
        observations=[];reports=[];pids=[];reference_observation=decode_capture(ref['captures'][0])
        for ordinal,capture in enumerate(captured['captures']):
            require(type(capture['repetition']) is int and capture['repetition']==ordinal,'Installed actual repeat slot differs')
            argv=[value['candidatePython'],'-I',str(source/SCRIPT),'--capture-candidate',str(origin/definition['id']/'request.json'),str(origin/definition['id']/('repeat-'+str(ordinal))/'observation.json')]
            validate_command(capture,argv,source);observation=decode_capture(capture);engine=observation['engine']
            validate_process_identity(engine,capture['command'],value['launcherPid'])
            pids.append(engine['pid'])
            require(engine['name']=='pyelk' and engine['isolated'] is True and engine['pathEmpty'] is True and engine['overridesAbsent'] is True and
                    engine['modulePath']==installed['modulePath'] and engine['version']==installed['version'] and engine['python']==installed['python'] and
                    engine['executable']==value['candidatePython'],'Installed actual engine/interpreter/isolation differs')
            exact(engine['sourceSha256'],{k:v for k,v in installed['packageFilesSha256'].items() if k.endswith('.py')},'Actual captured installed Python bytes differ')
            reports.append(compare_case(definition,raw,reference_observation,observation));observations.append(observation)
            times=measured_values(observation);timed_cases+=bool(times);nonzero+=sum(x!=0 for x in times)
        request=embedded_json(raw);request['_sha']=digest(raw)
        hashes=[digest(canonical(contract(observation_view(x,request,reference=False)))) for x in observations]
        require(len(set(hashes))==1,'Native independent repetitions differ outside generated timing leaves')
        require(len(set(pids))==value['repeat'],'Native repetition reused actual process identity')
        rows.append({'id':definition['id'],'passed':True,'repeat':value['repeat'],'classification':reports[0]['classification'],
                     'rawStrictPassed':[x['rawStrictPassed'] for x in reports], 'geometryPassed':definition['expectedOutcome']=='returned'})
    require(nonzero>0,'No nonzero real installed wall measurement was observed')
    host=validate_probe_receipt(value['hostProbe'],value,'host',root)
    lifecycle=validate_probe_receipt(value['lifecycleProbe'],value,'lifecycle',root)
    layout_seconds=sum(c['command']['elapsedSeconds'] for row in value['cases'] for c in row['captures'])
    probe_seconds=sum(c['command']['elapsedSeconds'] for kind in ('hostProbe','lifecycleProbe') for c in value[kind]['captures'])
    require(finite(value['layoutCaptureSeconds']) and value['layoutCaptureSeconds']>=layout_seconds-1e-5 and
            finite(value['captureSeconds']) and value['captureSeconds']>=value['layoutCaptureSeconds'] and
            value['captureSeconds']>=layout_seconds+probe_seconds-1e-5,'Serial capture timing contradicts actual command durations')
    return {'passed':True,'status':'E09_INSTALLED_COVERAGE_VALIDATED','caseCount':len(rows),'masterCount':25,
        'repeat':value['repeat'],'actualCandidateProcesses':len(rows)*value['repeat'],'cases':rows,
        'hostProbeValidated':True,'hostProbeCount':host['publicCaseCount'],'lifecycleProbeValidated':True,
        'actualAdditionalProbeProcesses':2*value['repeat'],'timedCaseCaptureCount':timed_cases,'nonzeroMeasuredLeafCount':nonzero,
        'historicalExecutionAuthenticated':False,'limitation':'Finite bounded requests and source branch witnesses; not all graphs or full upstream algorithm acceptance. Real timings are retained, not asserted equal across engines.'}

def capture_candidate(out,python,wheel,repeat=3):
    require(type(repeat) is int and repeat>=3,'Use at least three independent candidate processes')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);python=str(Path(python).resolve());wheel=Path(wheel).resolve()
    source_start=sources();env=os.environ.copy()
    for key in list(env):
        if key.upper() in OVERRIDES:env.pop(key)
    env['PATH']='';folder=out/'installed-command';folder.mkdir()
    command=run_candidate([python,'-I',str(ROOT/'scripts/verify_installed_wheel.py'),str(wheel),'--out',str(out/'installed-wheel.json')],folder,env)
    require(command['exitCode']==0,'Actual installed-wheel identity failed')
    installed_command=command_blob(folder,command);installed=load(out/'installed-wheel.json')
    validate_installed_identity(installed)
    cases=[];start=time.monotonic()
    for definition in suite()['cases']:
        parent=out/definition['id'];parent.mkdir();raw=(ROOT/SUITE/definition['request']).read_bytes();(parent/'request.json').write_bytes(raw);captures=[]
        for ordinal in range(repeat):
            folder=parent/('repeat-'+str(ordinal));folder.mkdir()
            command=run_candidate([python,'-I',str(ROOT/SCRIPT),'--capture-candidate',str(parent/'request.json'),str(folder/'observation.json')],folder,env)
            require(command['exitCode']==0 and command['timedOut'] is False,'Actual installed coverage failed: '+definition['id'])
            captures.append({'repetition':ordinal,**command_blob(folder,command),'observationBytesBase64':b64((folder/'observation.json').read_bytes()),'observationSha256':sha256(folder/'observation.json')})
        cases.append({'definition':definition,'requestBytesBase64':b64(raw),'captures':captures})
    value={'schema':'py-elk-e09-installed-coverage/v1','actualSourceRoot':str(ROOT),'actualExecutionRoot':str(out),
        'candidatePython':python,'wheel':str(wheel),'installed':installed,'installedCommand':installed_command,'launcherPid':os.getpid(),
        'installedReceiptBytesBase64':b64((out/'installed-wheel.json').read_bytes()),'repeat':repeat,
        'sourceSha256':source_start,'cases':cases,'layoutCaptureSeconds':time.monotonic()-start}
    for kind in ('host','lifecycle'):value[kind+'Probe']=capture_probe(out,python,env,repeat,kind)
    value['captureSeconds']=time.monotonic()-start
    exact(sources(),source_start,'Coverage tooling/dependencies changed during actual execution')
    write(out/'receipt.json',value);result=validate_candidate_receipt(value);write(out/'report.json',result);return result

def lifecycle_module(root=ROOT):
    import importlib.util
    path=Path(root)/'tools/reference/e09_host_lifecycle_probe.py'
    spec=importlib.util.spec_from_file_location('e09_host_lifecycle_probe',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def capture_probe(out,python,env,repeat,kind):
    if kind=='host':
        raw=(ROOT/HOST_REQUEST).read_bytes();(out/'host-request.json').write_bytes(raw)
    captures=[]
    for ordinal in range(repeat):
        folder=out/(kind+'-probe')/('repeat-'+str(ordinal));folder.mkdir(parents=True)
        if kind=='host':argv=[python,'-I',str(ROOT/SCRIPT),'--capture-host',str(out/'host-request.json'),str(folder/'observation.json')]
        else:argv=[python,'-I',str(ROOT/'tools/reference/e09_host_lifecycle_probe.py'),'--capture',str(folder/'observation.json')]
        command=run_candidate(argv,folder,env);require(command['exitCode']==0 and command['timedOut'] is False,'Actual '+kind+' probe failed')
        captures.append({'repetition':ordinal,**command_blob(folder,command),
            'observationBytesBase64':b64((folder/'observation.json').read_bytes()),'observationSha256':sha256(folder/'observation.json')})
    return {'requestBytesBase64':b64(raw) if kind=='host' else None,'captures':captures}

def validate_probe_receipt(probe,parent,kind,root=ROOT):
    require(len(probe['captures'])==parent['repeat'],'Actual '+kind+' probe repetitions missing')
    source=historical_path(parent['actualSourceRoot']);origin=historical_path(parent['actualExecutionRoot']);pids=[];result=None
    if kind=='host':
        raw=unb64(probe['requestBytesBase64']);require(raw==(Path(root)/HOST_REQUEST).read_bytes(),'Host original request bytes differ');request=embedded_json(raw)
    else:require(probe['requestBytesBase64'] is None,'Lifecycle probe has no input request protocol')
    for ordinal,capture in enumerate(probe['captures']):
        require(type(capture['repetition']) is int and capture['repetition']==ordinal,'Actual '+kind+' probe repeat slot differs')
        output=str(origin/(kind+'-probe')/('repeat-'+str(ordinal))/'observation.json')
        if kind=='host':argv=[parent['candidatePython'],'-I',str(source/SCRIPT),'--capture-host',str(origin/'host-request.json'),output]
        else:argv=[parent['candidatePython'],'-I',str(source/'tools/reference/e09_host_lifecycle_probe.py'),'--capture',output]
        validate_command(capture,argv,source);observation=decode_capture(capture);engine=observation['engine'];installed=parent['installed']
        require(engine['name']=='pyelk' and engine['version']==installed['version'] and engine['modulePath']==installed['modulePath'] and
                engine['executable']==parent['candidatePython'] and engine['python']==installed['python'] and engine['isolated'] is True and
                engine['pathEmpty'] is True and engine['overridesAbsent'] is True,'Actual '+kind+' installed engine/isolation differs')
        validate_process_identity(engine,capture['command'],parent['launcherPid'])
        exact(engine['sourceSha256'],{k:v for k,v in installed['packageFilesSha256'].items() if k.endswith('.py')},'Probe actual installed Python bytes differ')
        pids.append(engine['pid'])
        if kind=='host':
            require(observation['requestSha256']==digest(raw),'Actual host input SHA differs');result=validate_host_observation(observation,request,root)
        else:result=lifecycle_module(root).validate_lifecycle_observation(observation)
    require(len(set(pids))==parent['repeat'],'Actual '+kind+' probes reused a process identity')
    return result

def check(root=ROOT):
    result=verify_reference(load(Path(root)/RECORD),root)
    return {**result,'status':'E09_FIXED_REFERENCE_VALIDATED'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path)
    parser.add_argument('--with-reference',action='store_true');parser.add_argument('--package',type=Path,default=ROOT/'.local/npm-elkjs/package')
    parser.add_argument('--node',default='node');parser.add_argument('--repeat',type=int,default=3)
    parser.add_argument('--candidate-python');parser.add_argument('--wheel',type=Path)
    parser.add_argument('--verify-candidate',type=Path);parser.add_argument('--capture-candidate',nargs=2)
    parser.add_argument('--capture-host',nargs=2)
    parser.add_argument('--historical',action='store_true',help='Pure sealed E09/E10 archive verification; no current package acceptance')
    args=parser.parse_args()
    if args.historical:
        require(not any((args.capture_candidate,args.capture_host,args.with_reference,args.candidate_python,args.verify_candidate)),
                'Historical verification cannot capture or verify a current candidate')
        from iteration.e11_history import check as check_history
        result=check_history()
        if args.out:write(args.out,result)
        print(json.dumps(result))
        if not result['passed']:raise SystemExit(1)
        return
    if args.capture_candidate:
        require(bool(sys.flags.isolated),'Candidate capture requires -I');asyncio.run(candidate_capture(*args.capture_candidate));return
    if args.capture_host:
        require(bool(sys.flags.isolated),'Host capture requires -I');asyncio.run(host_capture(*args.capture_host));return
    if args.with_reference:
        require(args.out is not None,'--out required');result=capture_reference(args.out,args.package,args.node,args.repeat)
    elif args.candidate_python:
        require(args.out is not None and args.wheel is not None,'--out and --wheel required');result=capture_candidate(args.out,args.candidate_python,args.wheel,args.repeat)
    elif args.verify_candidate:result=validate_candidate_receipt(load(args.verify_candidate))
    else:result=check()
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','semantics')}))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps({'passed':False,'error':str(error)}));raise SystemExit(1)
