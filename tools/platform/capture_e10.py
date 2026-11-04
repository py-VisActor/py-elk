"""Small installed-platform observations; no pure validators or src imports.

Execute with the selected Python -I and an empty PATH from outside the repo.
Only this collector, the wheel identity helper and original requests are its
project execution dependencies. No full suite or upstream runtime is invoked.
"""
from __future__ import annotations
import argparse
import asyncio
import copy
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS', 'NODE_PATH'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load(path):
    return json.loads(Path(path).read_bytes())


def error_record(error):
    return {'type': type(error).__name__, 'code': getattr(error, 'code', None),
            'path': getattr(error, 'path', None), 'message': getattr(error, 'message', str(error)), 'string': str(error)}


def pid_probe(pid):
    if os.name == 'nt':
        from ctypes import wintypes
        dll = ctypes.WinDLL('kernel32', use_last_error=True)
        dll.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        dll.OpenProcess.restype = wintypes.HANDLE
        dll.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        dll.GetExitCodeProcess.restype = wintypes.BOOL
        dll.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = dll.OpenProcess(0x1000, False, pid)
        if not handle:
            code = ctypes.get_last_error()
            if code not in (87, 1168):
                raise RuntimeError('Cannot establish actual child PID state: '+str(code))
            return {'method': 'OpenProcess/GetExitCodeProcess', 'pid': pid, 'opened': False, 'error': code, 'alive': False}
        try:
            exit_code = wintypes.DWORD()
            if not dll.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                raise ctypes.WinError(ctypes.get_last_error())
            return {'method': 'OpenProcess/GetExitCodeProcess', 'pid': pid, 'opened': True,
                    'exitCode': exit_code.value, 'alive': exit_code.value == 259}
        finally:
            dll.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return {'method': 'kill(pid,0)', 'pid': pid, 'error': 'ESRCH', 'alive': False}
    return {'method': 'kill(pid,0)', 'pid': pid, 'error': None, 'alive': True}


def summary(trace):
    return {'phaseCount': len(trace), 'processors': [row['processor'] for row in trace],
            'outcomes': [row['outcome'] for row in trace]}


async def layout_case(ELK, definition, raw, engine):
    request = json.loads(raw)
    graph, constructor, arguments = (copy.deepcopy(request[key]) for key in ('graph', 'constructor', 'layoutArguments'))
    observation = {'schema': 'py-elk-layout-observation/v1', 'requestSha256': digest(raw), 'engine': engine,
        'inputBefore': copy.deepcopy(graph), 'constructorBefore': copy.deepcopy(constructor),
        'argumentsBefore': copy.deepcopy(arguments), 'clock': {'startMs': time.time_ns()//1_000_000}}
    instance = ELK(constructor)
    try:
        try:
            observation.update(outcome='returned', result=await instance.layout(graph, arguments))
        except Exception as error:
            record = error_record(error)
            observation.update(outcome='threw', error={'name': record['type'], 'message': record['string']},
                               errorDetails={key: record[key] for key in ('code', 'path', 'message')})
        observation['clock']['endMs'] = time.time_ns()//1_000_000
        observation.update(inputAfter=graph, constructorAfter=constructor, argumentsAfter=arguments,
                           traceSummary=summary(instance.last_trace))
    finally:
        instance.terminateWorker()
    observation.update(termination={'outcome': 'returned'}, closedSnapshot=instance._controller.snapshot())
    import base64
    return {'id': definition['id'], 'definition': definition, 'request': request,
            'requestSha256': digest(raw), 'requestBytesBase64': base64.b64encode(raw).decode(), 'observation': observation}


async def metadata_probe(ELK, graph):
    instance = ELK(); queries = {}
    for method, key in (('knownLayoutAlgorithms', 'algorithms'), ('knownLayoutOptions', 'options'), ('knownLayoutCategories', 'categories')):
        queries[key] = await getattr(instance, method)()
    instance.terminateWorker()
    result = {'queries': queries, 'closedQueryErrors': {}}
    for method in ('knownLayoutAlgorithms', 'knownLayoutOptions', 'knownLayoutCategories'):
        try:
            await getattr(instance, method)()
        except Exception as error:
            result['closedQueryErrors'][method] = error_record(error)
        else:
            raise RuntimeError('Closed metadata query unexpectedly returned')
    try:
        await instance.layout(copy.deepcopy(graph))
    except Exception as error:
        result['closedLayoutError'] = error_record(error)
    else:
        raise RuntimeError('Closed layout unexpectedly returned')
    result['closedSnapshot'] = instance._controller.snapshot()
    return result


async def cancellation_probe(ELK, graph, recovery):
    instance = ELK(); original = copy.deepcopy(graph); before = digest(canonical(graph))
    started = time.monotonic(); task = asyncio.create_task(instance.layout(graph)); events = []
    try:
        while time.monotonic()-started < 20:
            snapshot = instance._controller.snapshot()
            if task.done():
                await task
                raise RuntimeError('Layout finished before an actual running cancellation window was observed')
            job = next((row for row in snapshot['jobs'] if row['job_id'] == snapshot['running']), None)
            progress = None if job is None else job['progress']
            if progress is not None and progress['index'] >= 1 and progress['previous_outcome'] == 'returned' and snapshot['worker_alive']:
                live = pid_probe(job['pid'])
                if live['alive']:
                    events.append({'observedAt': time.monotonic(), 'snapshot': snapshot})
                    break
            await asyncio.sleep(0.001)
        if not events:
            raise RuntimeError('No real running phase/PID observed; queued cancellation is insufficient')
        result = {'inputBeforeSha256': before, 'phaseEvents': events, 'taskDoneBeforeCancel': task.done(),
                  'pidBeforeCancel': live, 'cancelRequestedAt': time.monotonic()}
        if result['taskDoneBeforeCancel']:
            raise RuntimeError('Cancellation task had already completed')
        task.cancel()
        try:
            await task
        except asyncio.CancelledError as error:
            result['cancelledErrorType'] = type(error).__name__
        else:
            raise RuntimeError('Running layout did not propagate actual cancellation')
        result.update(pidAfterCancel=pid_probe(live['pid']), afterCancel=instance._controller.snapshot(),
                      inputAfterSha256=digest(canonical(graph)))
        if graph != original:
            raise RuntimeError('Cancellation modified caller graph')
        result['recoveryResult'] = await instance.layout(copy.deepcopy(recovery['graph']), copy.deepcopy(recovery['layoutArguments']))
        result['recoveryTrace'] = instance.last_trace
        result['afterRecovery'] = instance._controller.snapshot()
        return result
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        instance.terminateWorker()
        if 'result' in locals():
            result['closedSnapshot'] = instance._controller.snapshot()


async def capture(wheel, suite):
    if not sys.flags.isolated or os.environ.get('PATH') != '' or any(key.upper() in OVERRIDES for key in os.environ):
        raise RuntimeError('Use Python -I, empty PATH and absent override variables')
    if Path.cwd().resolve().is_relative_to(ROOT):
        raise RuntimeError('Platform capture working directory must be outside the repository')
    helper_path = ROOT/'scripts/verify_installed_wheel.py'
    definition_path = suite/'cases.json'; definitions_raw = definition_path.read_bytes(); definitions = json.loads(definitions_raw)
    if definitions['schema'] != 'py-elk-e10-platform-suite/v1' or len(definitions['cases']) != 6:
        raise RuntimeError('Expected the frozen six-case platform suite')
    requests = [(definition, suite/definition['request'], (suite/definition['request']).read_bytes())
                for definition in definitions['cases']]
    cancel_path = ROOT/definitions['cancelRequest']['path']; cancel_raw = cancel_path.read_bytes()
    paths = [Path(__file__).resolve(), helper_path, definition_path, *[path for _,path,_ in requests], cancel_path]
    initial_dependencies = {path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in paths}
    if initial_dependencies[definition_path.relative_to(ROOT).as_posix()] != digest(definitions_raw) or any(
            initial_dependencies[path.relative_to(ROOT).as_posix()] != digest(raw) or digest(raw) != definition['requestSha256']
            for definition,path,raw in requests) or digest(cancel_raw) != definitions['cancelRequest']['sha256']:
        raise RuntimeError('Original platform request/dependency changed before capture')
    import pyelk
    from pyelk import ELK
    spec = importlib.util.spec_from_file_location('_e10_installed_identity', helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    installed = helper.verify(wheel)
    base = Path(getattr(sys, '_base_executable', sys.executable)).resolve()
    engine = {'name': 'pyelk', 'version': pyelk.__version__, 'implementation': sys.implementation.name,
        'python': sys.version, 'versionInfo': list(sys.version_info[:3]),
        'executable': sys.executable, 'executableSha256': digest(Path(sys.executable).read_bytes()),
        'baseExecutable': str(base), 'baseExecutableSha256': digest(base.read_bytes()), 'prefix': sys.prefix, 'basePrefix': sys.base_prefix,
        'isolated': bool(sys.flags.isolated), 'pid': os.getpid(), 'parentPid': os.getppid(),
        'platform': {'system': platform.system(), 'release': platform.release(), 'version': platform.version(), 'machine': platform.machine()},
        'pathEmpty': os.environ.get('PATH') == '', 'overridesAbsent': not any(key.upper() in OVERRIDES for key in os.environ)}
    value = {'schema': 'py-elk-e10-platform-observation/v1', 'engine': engine, 'installed': installed,
             'cases': [], 'captureInterval': {'clock': 'time.monotonic', 'started': time.monotonic()}}
    recovery = None
    for definition,path,raw in requests:
        value['cases'].append(await layout_case(ELK, definition, raw, engine))
        if definition['id'] == 'layered-chain': recovery = json.loads(raw)
    value['metadata'] = await metadata_probe(ELK, recovery['graph'])
    value['cancel'] = await cancellation_probe(ELK, json.loads(cancel_raw)['cpuGraph'], recovery)
    value['cancel']['recoveryRequestSha256'] = next(row['requestSha256'] for row in definitions['cases'] if row['id'] == 'layered-chain')
    value['captureInterval']['finished'] = time.monotonic()
    final_dependencies = {path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in paths}
    if final_dependencies != initial_dependencies:
        raise RuntimeError('Platform execution dependencies changed during capture')
    value['executionDependencies'] = initial_dependencies
    value['fullValidation'] = False
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', required=True, type=Path)
    parser.add_argument('--suite', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists(): raise FileExistsError(args.out)
    result = asyncio.run(capture(args.wheel.resolve(), args.suite.resolve()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2); stream.write('\n')


if __name__ == '__main__':
    main()
