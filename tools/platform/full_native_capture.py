"""Actual installed-wheel public calls, native OS CPU cancellation and recovery."""
import argparse
import asyncio
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time
import zipfile
from email.parser import BytesParser

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = {'PYTHONPATH','PYTHONHOME','NODE_OPTIONS','NODE_PATH'}
sys.path.insert(0, str(ROOT/'tools/reference'))
sys.path.insert(0, str(ROOT/'scripts'))
from native_process_probe import cpu_graph, wait_for_cpu
from e09_host_lifecycle_probe import pid_probe
from verify_installed_wheel import verify
from layout_checks import diff, _project_reference_shape_hashes


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text('utf-8'))


async def capture(args):
    if not sys.flags.isolated or os.environ.get('PATH') != '' or any(k.upper() in OVERRIDES for k in os.environ):
        raise RuntimeError('Capture requires -I, empty PATH and absent overrides')
    if Path.cwd().resolve().is_relative_to(ROOT): raise RuntimeError('Capture must run outside repository')
    import pyelk
    from pyelk import ELK
    package=Path(pyelk.__file__).resolve().parent
    if package.is_relative_to(ROOT): raise RuntimeError('Installed capture imported repository code')
    bindings=[Path(__file__),ROOT/'scripts/verify_installed_wheel.py',ROOT/'scripts/layout_checks.py',
              ROOT/'tools/reference/native_process_probe.py',ROOT/'tools/reference/e09_host_lifecycle_probe.py',
              args.request,args.oracle,args.installed_wheel,ROOT/'tests/fixtures/suites/full-native-core/metadata-expected.json']
    initial={str(p):sha(p)for p in bindings}
    installed=verify(args.installed_wheel)
    with zipfile.ZipFile(args.wheel)as archive:
        official_payload={name[len('pyelk/'):]:hashlib.sha256(archive.read(name)).hexdigest()
                          for name in archive.namelist()if name.startswith('pyelk/')and not name.endswith('/')}
        metadata_name=next(name for name in archive.namelist()if name.endswith('.dist-info/METADATA'))
        official_metadata=archive.read(metadata_name)
    actual_metadata=base64.b64decode(installed['distributionMetadata']['bytesBase64'])
    assert installed['packageFilesSha256']==official_payload,'Rebuilt sdist runtime payload differs from canonical wheel'
    metadata_exact=official_metadata==actual_metadata
    # RFC822 metadata permits CRLF/LF. Preserve both originals and disclose the
    # only accepted source-build text transformation; runtime bytes stay exact.
    metadata_newlines_only=official_metadata.replace(b'\r\n',b'\n')==actual_metadata.replace(b'\r\n',b'\n')
    parsed_official=BytesParser().parsebytes(official_metadata);parsed_actual=BytesParser().parsebytes(actual_metadata)
    assert list(parsed_official.items())==list(parsed_actual.items()),'Rebuilt metadata headers differ'
    assert parsed_official.get_payload().replace('\r\n','\n')==parsed_actual.get_payload().replace('\r\n','\n'),'Rebuilt metadata body differs'
    assert metadata_newlines_only,'Rebuilt metadata has differences beyond CRLF/LF'
    request=load(args.request);oracle=load(args.oracle)
    assert oracle['requestSha256']==sha(args.request) and oracle['outcome']=='returned'
    assert oracle['engine']['entrypointSha256']=='b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7'
    graph=copy.deepcopy(request['graph']);before=copy.deepcopy(graph)
    elk=ELK(request['constructor'])
    body={'schema':'pyelk-full-installed-platform-observation/v1','installed':installed,
          'engine':{'platform':platform.system(),'machine':platform.machine(),'versionInfo':list(sys.version_info[:3]),
                    'python':sys.version,'executable':sys.executable,'basePrefix':sys.base_prefix,'prefix':sys.prefix,
                    'executableSha256':sha(sys.executable),'pid':os.getpid(),'parentPid':os.getppid(),
                    'isolated':bool(sys.flags.isolated),'cwd':str(Path.cwd()),'pathEmpty':True,'overridesAbsent':True},
          'wheelSha256':sha(args.wheel),'installedWheelSha256':sha(args.installed_wheel),
          'canonicalRuntimePayloadExact':True,'metadataArtifactComparison':{
              'rawExact':metadata_exact,'CRLFtoLFOnly':metadata_newlines_only,'parsedHeadersExact':True,'parsedBodyExactAfterDeclaredNewlines':True,
              'canonicalMetadataSha256':hashlib.sha256(official_metadata).hexdigest(),
              'installedMetadataSha256':hashlib.sha256(actual_metadata).hexdigest(),
              'canonicalMetadataBytesBase64':base64.b64encode(official_metadata).decode(),
              'policy':'Only RFC822 CRLF/LF line endings may differ for a separately built sdist wheel; all208 runtime file bytes must match canonical wheel'},
          'requestSha256':sha(args.request),'oracleSha256':sha(args.oracle)}
    try:
        metadata={'algorithms':await elk.knownLayoutAlgorithms(),'options':await elk.knownLayoutOptions(),'categories':await elk.knownLayoutCategories()}
        expected=load(ROOT/'tests/fixtures/suites/full-native-core/metadata-expected.json')['expectedQueries']['default']
        body['metadata']={'counts':{key:len(value)for key,value in metadata.items()},'comparison':diff(expected,metadata,tolerant=False)}
        started=time.perf_counter();actual=await elk.layout(graph,request['layoutArguments'])
        reference=copy.deepcopy(oracle['result']);adaptations=[];violations=[]
        _project_reference_shape_hashes(before,reference,actual,prefix='/result',adaptations=adaptations,violations=violations)
        body['layout']={'elapsedSeconds':time.perf_counter()-started,'result':actual,'rawComparison':diff(oracle['result'],actual,tolerant=False),
                        'comparison':diff(reference,actual,tolerant=False),'adaptations':adaptations,'violations':violations,
                        'inputPreservation':diff(before,graph,tolerant=False),'trace':elk.last_trace}
        body['layout']['snapshot']=elk._controller.snapshot()
    finally: elk.close()
    # A separate real Force job supplies an OS CPU window; no busy test worker.
    running=ELK();task=asyncio.create_task(running.layout(cpu_graph(iterations=20000)))
    try:
        sampled=await wait_for_cpu(running,task,minimum_seconds=.02)
        pid=sampled['snapshots'][-1]['worker_pid'];alive=pid_probe(pid)
        task.cancel()
        try: await task
        except asyncio.CancelledError: canceled=True
        else: raise AssertionError('Running cancellation returned normally')
        after=running._controller.snapshot();dead=pid_probe(pid)
        recovered=await running.layout(copy.deepcopy(before),request['layoutArguments'])
        recovered_snapshot=running._controller.snapshot();recovery_pid=recovered_snapshot['worker_pid']
        recovery_alive=pid_probe(recovery_pid)
        running.close();closed=running._controller.snapshot();recovery_dead=pid_probe(recovery_pid)
        try: await running.knownLayoutAlgorithms()
        except Exception as error: closed_error={'type':type(error).__name__,'code':getattr(error,'code',None)}
        else: raise AssertionError('Closed metadata query returned')
        body['cancelRecoveryClose']={'cpuEvidence':sampled,'pidBefore':alive,'pidAfterCancel':dead,'cancelled':canceled,
            'afterCancel':after,'recoveryResult':recovered,'recoveryComparison':diff(actual,recovered,tolerant=False),
            'recoverySnapshot':recovered_snapshot,'recoveryPidBeforeClose':recovery_alive,'recoveryPidAfterClose':recovery_dead,
            'closedSnapshot':closed,'closedQueryError':closed_error}
        assert sampled['cpuSeconds'][1]>sampled['cpuSeconds'][0] and alive['alive'] and not dead['alive']
        assert after['pending']==0 and not after['worker_alive'] and not after['dispatcher_alive']
        assert recovery_alive['alive'] and not recovery_dead['alive'] and closed['state']=='closed' and not closed['worker_alive']
        assert closed_error=={'type':'ResourceClosedError','code':'RESOURCE_CLOSED'}
    finally:
        if not task.done():
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
        running.close()
    body['bindingsSha256']=initial
    assert initial=={str(p):sha(p)for p in bindings},'Capture input/helper changed during execution'
    after_identity=verify(args.installed_wheel)
    assert after_identity['packageFilesSha256']==installed['packageFilesSha256']
    body['passed']=(body['metadata']['comparison']['passed'] and body['layout']['comparison']['passed'] and
                    body['layout']['inputPreservation']['passed'] and not violations and
                    body['cancelRecoveryClose']['recoveryComparison']['passed'])
    return body


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--wheel',type=Path,required=True)
    parser.add_argument('--installed-wheel',type=Path)
    parser.add_argument('--request',type=Path,required=True);parser.add_argument('--oracle',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.installed_wheel=args.wheel if args.installed_wheel is None else args.installed_wheel
    body=asyncio.run(capture(args))
    with args.out.open('x',encoding='utf-8')as stream:json.dump(body,stream,indent=2,allow_nan=False)
    print(json.dumps({'passed':body['passed'],'platform':body['engine']['platform'],'version':body['engine']['versionInfo'],
                      'installedFiles':len(body['installed']['packageFilesSha256']),'metadata':body['metadata']['counts']}))
    raise SystemExit(0 if body['passed']else 1)
