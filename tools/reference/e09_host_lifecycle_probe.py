"""E09 installed host probes, independent of the product package at import time.

Private busy/fault workers exercise host boundaries only. The running-deadline
probe uses the real installed worker plus independently sampled OS CPU time.
Full runtime exposes one coordinator progress entry, not invented phase events.
"""
from __future__ import annotations
import argparse
import asyncio
import copy
import ctypes
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'NODE_PATH', 'NODE_OPTIONS'}
SCHEMA = 'py-elk-full-host-lifecycle-observation/v2'
NATIVE_PROCESSORS = ('RecursiveLayoutEngine',)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def error_record(error):
    return {'type': type(error).__name__, 'code': getattr(error, 'code', None),
            'path': getattr(error, 'path', None), 'message': getattr(error, 'message', str(error)), 'string': str(error)}


def small_graph():
    return {'id': 'e09-probe', 'layoutOptions': {'elk.randomSeed': '7'},
            'children': [{'id': 'a', 'width': 20, 'height': 10}, {'id': 'b', 'width': 20, 'height': 10}],
            'edges': [{'id': 'e', 'sources': ['a'], 'targets': ['b']}]}


def cpu_graph():
    from native_process_probe import cpu_graph as actual_cpu_graph
    return actual_cpu_graph()


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
            error = ctypes.get_last_error()
            if error not in (87, 1168):
                raise RuntimeError('Cannot establish PID state: '+str(error))
            return {'method': 'OpenProcess/GetExitCodeProcess', 'pid': pid, 'opened': False, 'error': error, 'alive': False}
        code = wintypes.DWORD()
        try:
            if not dll.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            return {'method': 'OpenProcess/GetExitCodeProcess', 'pid': pid, 'opened': True,
                    'exitCode': code.value, 'alive': code.value == 259}
        finally:
            dll.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return {'method': 'kill(pid,0)', 'pid': pid, 'error': 'ESRCH', 'alive': False}
    return {'method': 'kill(pid,0)', 'pid': pid, 'error': None, 'alive': True}


async def wait_for(instance, predicate, timeout=15):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        snapshot = instance._controller.snapshot()
        if predicate(snapshot):
            return snapshot
        await asyncio.sleep(0.001)
    raise AssertionError('Lifecycle observation not reached: '+str(instance._controller.snapshot()))


def _job_input(connection, constructor_tokens):
    from pyelk.execution.wire_codec import decode_json_tree
    constructor = decode_json_tree(constructor_tokens)
    message = connection.recv()
    return message['job_id'], decode_json_tree(message['graph_tokens']), constructor, decode_json_tree(message['argument_tokens'])


def private_busy_worker(connection, constructor_tokens):
    """Private host-control CPU, never represented as a layout phase."""
    _job_input(connection, constructor_tokens)
    value = 1
    while True:
        value = (value*17+3) % 2147483647


class _RecordingConnection:
    def __init__(self, connection, output):
        self.connection, self.output, self.messages = connection, output, []

    def send(self, message):
        self.messages.append(message)
        Path(self.output).write_text(json.dumps(self.messages, allow_nan=False), encoding='utf8')
        self.connection.send(message)

    def close(self):
        self.connection.close()


def private_protocol_worker(connection, constructor_tokens):
    from pyelk.execution.wire_codec import encode_json_tree
    job_id, graph, constructor, arguments = _job_input(connection, constructor_tokens)
    kind = graph['business']['fault']
    messages = {'unknownKind': {'kind': 'E09_UNKNOWN', 'job_id': job_id},
                'wrongJob': {'kind': 'result', 'job_id': job_id+1, 'graph_tokens': encode_json_tree({}), 'trace': [], 'pid': os.getpid(), 'process_time': time.process_time()},
                'badBody': {'kind': 'progress', 'job_id': job_id, 'index': True}}
    recorded = _RecordingConnection(connection, graph['business']['rawPath'])
    recorded.send(messages[kind])
    recorded.close()


def private_import_worker(connection, constructor_tokens):
    from pyelk.execution.full_worker import _execute
    from pyelk.execution.runtime import NativeRuntime
    job_id, graph, constructor, arguments = _job_input(connection, constructor_tokens)
    def missing_import(*args, **kwargs):
        __import__('E09_DELIBERATELY_MISSING_MODULE')
    runtime = NativeRuntime(constructor)
    runtime.layout = missing_import
    _execute(_RecordingConnection(connection, graph['business']['rawPath']), runtime, job_id, graph, arguments)
    connection.close()


async def recover(instance):
    result = await instance.layout(small_graph())
    snapshot = await wait_for(instance, lambda s: s['pending'] == 0 and not s['dispatcher_alive'])
    return snapshot, result, instance.last_trace


async def _attempt(ELK, graph, timeout):
    from native_process_probe import process_cpu_seconds
    instance = ELK(timeout=timeout)
    called = time.monotonic()
    task = asyncio.create_task(instance.layout(graph))
    events, alive = [], None
    handed_off = False
    try:
        while not task.done():
            snapshot = instance._controller.snapshot()
            jobs = [job for job in snapshot['jobs'] if job['state'] == 'running' and job['progress'] is not None]
            observed_at = time.monotonic()
            if (jobs and snapshot['worker_alive'] and (timeout is None or observed_at < jobs[-1]['submitted_at']+timeout)
                    ):
                cpu = process_cpu_seconds(jobs[-1]['pid'])
                if cpu is not None and (not events or cpu > events[-1]['cpuSeconds']):
                    events.append({'observedAt': observed_at, 'snapshot': snapshot, 'cpuSeconds': cpu})
                alive = pid_probe(jobs[-1]['pid'])
            await asyncio.sleep(0.001)
        try:
            await task
            outcome, error = 'returned', None
        except Exception as caught:
            outcome, error = 'threw', error_record(caught)
        after = await wait_for(instance, lambda s: s['pending'] == 0 and not s['dispatcher_alive'])
        pid = after['jobs'][-1]['pid']
        body = {'timeout': timeout, 'submissionCalledAt': called, 'finishedAt': time.monotonic(),
                'phaseEvents': events, 'pidBefore': alive, 'pidAfter': None if pid is None else pid_probe(pid),
                'outcome': outcome, 'error': error, 'after': after}
        handed_off = True
        return body, instance
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if not handed_off:
            instance.terminateWorker()


def _qualified(attempt):
    events = attempt['phaseEvents']
    return (attempt['error'] is not None and attempt['error']['type'] == 'ExecutionTimeoutError'
            and len(events) >= 2 and events[-1]['cpuSeconds'] > events[0]['cpuSeconds'])


async def running_timeout_probe(ELK, folder):
    graph = cpu_graph(); before = fingerprint(graph)
    calibration, calibrated_instance = await _attempt(ELK, graph, None)
    calibrated_instance.terminateWorker()
    (folder/'deadline-calibration.json').write_text(json.dumps(calibration, allow_nan=False), encoding='utf8')
    if len(calibration['phaseEvents']) < 2:
        raise AssertionError('No independently observed OS CPU-running window in calibration')
    # Pick an actual measured point within real computation, not a sleep/barrier.
    event = calibration['phaseEvents'][len(calibration['phaseEvents'])//2]
    base = event['observedAt']-calibration['after']['jobs'][-1]['submitted_at']
    attempts = []
    for factor in (1.0, 1.08, 0.94, 1.16, 0.88, 1.04):
        attempt, instance = await _attempt(ELK, graph, max(0.02, base*factor))
        attempts.append(attempt)
        (folder/('deadline-attempt-'+str(len(attempts)-1)+'.json')).write_text(json.dumps(attempt, allow_nan=False), encoding='utf8')
        if _qualified(attempt):
            break
        instance.terminateWorker()
    if not _qualified(attempts[-1]):
        raise AssertionError('No real CPU-running deadline observed; no timeout acceptance claim')
    try:
        instance._controller._timeout = None
        after, result, trace = await recover(instance)
    finally:
        instance.terminateWorker()
    return {'inputBeforeSha256': before, 'inputAfterSha256': fingerprint(graph), 'calibration': calibration,
            'attempts': attempts, 'qualifiedAttempt': len(attempts)-1, 'afterRecovery': after,
            'recoveryResult': result, 'recoveryTrace': trace}


async def queued_timeout_probe(ELK):
    from pyelk.execution.full_worker import worker_main
    instance = ELK(max_pending=2); instance._controller._worker_target = private_busy_worker
    first = asyncio.create_task(instance.layout(small_graph()))
    second = None
    try:
        running = await wait_for(instance, lambda s: s['running'] is not None and s['worker_alive'])
        # This controls only a future submission's configured total deadline.
        instance._controller._timeout = 0.05
        second = asyncio.create_task(instance.layout(small_graph()))
        queued = await wait_for(instance, lambda s: bool(s['queued']))
        try:
            await second
        except Exception as error:
            failure = error_record(error)
        else:
            raise AssertionError('Queued deadline returned normally')
        expired = instance._controller.snapshot()
        if first.done():
            raise AssertionError('Queued-deadline fixture no longer occupied its worker')
        first.cancel()
        try:
            await first
        except asyncio.CancelledError:
            pass
        cancelled = await wait_for(instance, lambda s: s['pending'] == 0 and not s['dispatcher_alive'])
        instance._controller._timeout = None; instance._controller._worker_target = worker_main
        after, result, trace = await recover(instance)
        return {'fixture': 'private-busy-host-control', 'running': running, 'queued': queued,
                'afterQueuedTimeout': expired, 'queuedError': failure, 'afterCancel': cancelled,
                'afterRecovery': after, 'recoveryResult': result, 'recoveryTrace': trace}
    finally:
        for task in (first, second):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        instance.terminateWorker()


async def fault_probe(ELK, folder):
    import pyelk.execution.full_lifecycle as lifecycle
    from pyelk.execution.full_worker import worker_main
    records = {}
    for kind in ('unknownKind', 'wrongJob', 'badBody', 'internalImport', 'spawnFailure'):
        instance = ELK(); graph = small_graph(); output = folder/(kind+'-messages.json')
        graph['business'] = {'fault': kind, 'rawPath': str(output)}
        instance._controller._worker_target = private_import_worker if kind == 'internalImport' else private_protocol_worker
        try:
            if kind == 'spawnFailure':
                actual_context = lifecycle.multiprocessing.get_context('spawn')
                class StartFailure:
                    def __init__(self, inner): self.inner = inner
                    def start(self): raise RuntimeError('E09 deliberate spawn start failure')
                    def __getattr__(self, name): return getattr(self.inner, name)
                class Context:
                    def Pipe(self, **kwargs): return actual_context.Pipe(**kwargs)
                    def Process(self, **kwargs): return StartFailure(actual_context.Process(**kwargs))
                with patch.object(lifecycle.multiprocessing, 'get_context', return_value=Context()):
                    try: await instance.layout(graph)
                    except Exception as error: failure = error_record(error)
                    else: raise AssertionError('Injected spawn failure returned')
            else:
                try: await instance.layout(graph)
                except Exception as error: failure = error_record(error)
                else: raise AssertionError('Injected fault returned: '+kind)
            after = await wait_for(instance, lambda s: s['pending'] == 0 and not s['dispatcher_alive'])
            messages = json.loads(output.read_text()) if output.exists() else []
            # Internal algorithm errors preserve the persistent process; the
            # injected test runtime is intentionally retired before recovery.
            instance._controller._drop_runtime()
            instance._controller._worker_target = worker_main
            recovered, result, trace = await recover(instance)
            records[kind] = {'sentMessages': messages, 'error': failure, 'after': after,
                             'afterRecovery': recovered, 'recoveryResult': result, 'recoveryTrace': trace}
        finally:
            instance.terminateWorker()
    return records


async def cross_thread_close_probe(ELK):
    instance = ELK(max_pending=2); instance._controller._worker_target = private_busy_worker
    tasks = [asyncio.create_task(instance.layout(small_graph())) for _ in range(2)]
    try:
        before = await wait_for(instance, lambda s: s['running'] is not None and bool(s['queued']) and s['worker_alive'])
        pid = before['worker_pid']; alive = pid_probe(pid); main_thread = threading.get_ident()
        def close():
            start = time.monotonic(); value = instance.terminateWorker()
            return {'threadId': threading.get_ident(), 'startedAt': start, 'finishedAt': time.monotonic(), 'returnValue': value}
        call = await asyncio.to_thread(close)
        errors = []
        for task in tasks:
            try: await task
            except Exception as error: errors.append(error_record(error))
            else: raise AssertionError('Closed running/queued submission returned normally')
        after = instance._controller.snapshot(); second = instance.terminateWorker()
        return {'fixture': 'private-busy-host-control', 'runningAndQueued': before, 'pidBefore': alive,
                'threadCall': call, 'mainThreadId': main_thread, 'afterFirstClose': after,
                'secondReturnValue': second, 'afterSecondClose': instance._controller.snapshot(),
                'errors': errors, 'pidAfter': pid_probe(pid)}
    finally:
        instance.terminateWorker()
        for task in tasks:
            if not task.done(): task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def capture_lifecycle(ELK, folder):
    async def queries(instance):
        return {key: await getattr(instance, name)() for key, name in
                (('algorithms', 'knownLayoutAlgorithms'), ('options', 'knownLayoutOptions'), ('categories', 'knownLayoutCategories'))}
    instance = ELK()
    try:
        default = await queries(instance)
        await instance.layout(small_graph())
        trace_before_close = instance.last_trace
    finally:
        instance.terminateWorker()
    closed_trace = {'before': trace_before_close, 'after': instance.last_trace,
                    'closedSnapshot': instance._controller.snapshot()}
    aliases = []
    for algorithms in (['layered'], ['org.eclipse.elk.layered'], ['layered', 'org.eclipse.elk.layered', 'layered']):
        constructor = {'algorithms': algorithms}; before = fingerprint(constructor); instance = ELK(constructor)
        try: result = await queries(instance)
        finally: instance.terminateWorker()
        aliases.append({'constructor': constructor, 'constructorBeforeSha256': before,
                        'constructorAfterSha256': fingerprint(constructor), 'queries': result})
    try: ELK({'workerUrl': 'E09-unused-worker.js'})
    except Exception as error: worker_url = error_record(error)
    else: raise AssertionError('Unsupported workerUrl accepted')
    valid, invalid = [], []
    for maximum in (1, 64):
        instance = ELK(max_pending=maximum); before = instance._controller.snapshot(); instance.terminateWorker()
        valid.append({'maxPending': maximum, 'before': before, 'closed': instance._controller.snapshot()})
    for maximum in (0, 65, True):
        try: ELK(max_pending=maximum)
        except Exception as error: invalid.append({'value': maximum, 'error': error_record(error)})
        else: raise AssertionError('Invalid max_pending accepted')
    body = {'registry': {'default': default, 'aliases': aliases, 'workerUrlError': worker_url, 'closedTrace': closed_trace},
            'capacity': {'valid': valid, 'invalid': invalid}}
    for name, action in (('runningTimeout', lambda: running_timeout_probe(ELK, folder)),
                         ('queuedTimeout', lambda: queued_timeout_probe(ELK)),
                         ('faults', lambda: fault_probe(ELK, folder)),
                         ('crossThreadClose', lambda: cross_thread_close_probe(ELK))):
        body[name] = await action()
        (folder/'capture-progress.json').write_text(json.dumps(body, allow_nan=False), encoding='utf8')
    return body


async def capture_observation(folder, *, installed=True):
    if installed:
        if not sys.flags.isolated or os.environ.get('PATH') != '' or any(k.upper() in OVERRIDES for k in os.environ):
            raise ValueError('Capture requires -I, empty PATH and absent overrides')
    import pyelk
    package = Path(pyelk.__file__).resolve().parent
    if installed:
        distribution = importlib.metadata.distribution('py-elk')
        if package/'__init__.py' != Path(distribution.locate_file('pyelk/__init__.py')).resolve() or package.is_relative_to(ROOT/'src'):
            raise ValueError('Capture must import the genuine installed distribution')
    engine = {'name': 'pyelk', 'version': pyelk.__version__, 'modulePath': str(package), 'python': sys.version,
              'executable': sys.executable, 'isolated': bool(sys.flags.isolated), 'pid': os.getpid(), 'parentPid': os.getppid(),
              'pathEmpty': os.environ.get('PATH') == '', 'overridesAbsent': not any(k.upper() in OVERRIDES for k in os.environ),
              'sourceSha256': {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*.py'))}}
    start = time.monotonic(); body = await capture_lifecycle(pyelk.ELK, folder)
    return {'schema': SCHEMA, 'engine': engine,
            'captureInterval': {'clock': 'time.monotonic', 'started': start, 'finished': time.monotonic()}, **body}


def validate_full_snapshot(snapshot, interval):
    """Validate real persistent-worker leases, distinct from OS process reaping."""
    def require(condition, message):
        if not condition: raise ValueError(message)
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)
    fields = {'state','pending','queued','running','worker_pid','worker_alive','dispatcher_alive','last_submitted_id','jobs','worker_persistent'}
    require(type(snapshot) is dict and set(snapshot) == fields, 'Full snapshot field denominator differs')
    require(snapshot['worker_persistent'] is True and snapshot['state'] in ('new','open','closing','closed'), 'Full runtime identity/state differs')
    require(type(snapshot['pending']) is int and snapshot['pending'] >= 0 and type(snapshot['last_submitted_id']) is int, 'Invalid pending/job counter')
    require(type(snapshot['worker_alive']) is bool and type(snapshot['dispatcher_alive']) is bool, 'Invalid worker/dispatcher flags')
    worker = snapshot['worker_pid']
    require((worker is None or type(worker) is int and worker > 0) and snapshot['worker_alive'] is (worker is not None), 'Persistent worker PID/alive mismatch')
    jobs = snapshot['jobs']; require(type(jobs) is list, 'Invalid full jobs collection')
    ids = []; active = []
    for job in jobs:
        require(type(job) is dict and set(job) == {'job_id','state','pid','exitcode','reaped','lease_released','submitted_at','started_at','finished_at','progress'}, 'Full job field denominator differs')
        require(type(job['job_id']) is int and 0 < job['job_id'] <= snapshot['last_submitted_id'], 'Invalid full job ID')
        ids.append(job['job_id'])
        require(job['state'] in ('queued','running','returned','failed','cancelled') and type(job['reaped']) is bool and type(job['lease_released']) is bool, 'Invalid job state/reap/lease')
        pid = job['pid']; require(pid is None or type(pid) is int and pid > 0, 'Invalid full job PID')
        require(job['exitcode'] is None or type(job['exitcode']) is int, 'Invalid full exit code')
        stamps = [job[key] for key in ('submitted_at','started_at','finished_at') if job[key] is not None]
        require(job['submitted_at'] is not None and all(finite(stamp) and interval['started'] <= stamp <= interval['finished'] for stamp in stamps) and stamps == sorted(stamps), 'Job lifecycle clock mismatch')
        if job['state'] in ('queued','running'):
            active.append(job)
            require(job['finished_at'] is None, 'Active job already finished')
        else:
            require(job['lease_released'] is True and job['finished_at'] is not None, 'Terminal job lease not released')
            if not job['reaped']:
                require(pid == worker and snapshot['worker_alive'] and job['exitcode'] is None, 'Unreaped terminal job is not owned by the live persistent worker')
            if pid is None: require(job['started_at'] is None and job['exitcode'] is None and job['reaped'], 'Unspawned terminal job has process fields')
        if job['state'] == 'queued': require(pid is None and job['started_at'] is None, 'Queued job has started')
        if job['state'] == 'running': require(type(pid) is int and job['started_at'] is not None and pid == worker, 'Running job/worker identity mismatch')
        progress = job['progress']
        if progress is not None:
            require(type(progress) is dict and set(progress) == {'index','processor','previous_processor','previous_outcome','process_time'}, 'Full progress field denominator differs')
            require(type(progress['index']) is int and progress['index'] == 0 and progress['processor'] == 'RecursiveLayoutEngine' and progress['previous_processor'] is None and progress['previous_outcome'] is None and finite(progress['process_time']) and progress['process_time'] >= 0, 'Coordinator progress identity differs')
        if job['state'] == 'returned': require(progress is not None and pid is not None, 'Returned layout lacks actual coordinator entry')
    require(ids == sorted(set(ids)), 'Full job IDs duplicated/reordered')
    require(snapshot['pending'] == len(active), 'Full pending denominator differs')
    queued = snapshot['queued']
    require(type(queued) is list and all(type(value) is int for value in queued) and queued == sorted(set(queued)), 'Invalid FIFO IDs')
    require(set(queued) <= {job['job_id'] for job in active if job['state'] == 'queued'}, 'Queued ID/state mismatch')
    running = snapshot['running']
    require(sum(job['state'] == 'running' for job in active) <= 1, 'Multiple running jobs')
    if running is not None:
        require(type(running) is int and any(job['job_id'] == running and job['state'] == 'running' for job in active), 'Running slot identity mismatch')
    else: require(not any(job['state'] == 'running' for job in active), 'Running job missing slot')
    if not active: require(running is None and queued == [], 'Idle worker retains active queue')
    if snapshot['state'] == 'closed': require(not active and not snapshot['worker_alive'] and not snapshot['dispatcher_alive'], 'Closed runtime retains resources')


def validate_lifecycle_observation(value):
    """Pure verification of raw state, errors, phase CPU, identities and geometry."""
    sys.path.insert(0, str(ROOT/'scripts')) if str(ROOT/'scripts') not in sys.path else None
    from validate_e08_api import _os_pid
    from layout_checks import diff, geometry, load
    def require(condition, message):
        if not condition: raise ValueError(message)
    def finite(value):
        try: return type(value) in (int, float) and math.isfinite(value)
        except (OverflowError, ValueError): return False
    def os_pid(record, alive):
        if record['method'] == 'OpenProcess/GetExitCodeProcess':
            require(type(record['opened']) is bool, 'OS opened flag must be boolean')
        _os_pid(record, alive)
    def exact(actual, expected, message):
        require(diff(actual, expected)['passed'], message)
    def error(actual, name, code, path, message=None):
        require(set(actual) == {'type', 'code', 'path', 'message', 'string'}, 'Error field denominator differs')
        require(actual['type'] == name and actual['code'] == code and actual['path'] == path and type(actual['message']) is str, 'Error classification differs')
        if message is not None: require(actual['message'] == message, 'Error message differs')
        require(actual['string'] == code+' at '+(path or '/')+': '+actual['message'], 'Public error string differs')
    require(type(value) is dict and set(value) == {'schema', 'engine', 'captureInterval', 'registry', 'capacity', 'runningTimeout', 'queuedTimeout', 'faults', 'crossThreadClose'} and value['schema'] == SCHEMA, 'Unknown E09 lifecycle schema')
    engine = value['engine']
    require(engine['name'] == 'pyelk' and all(type(engine[k]) is str for k in ('version', 'modulePath', 'python', 'executable')),
            'Invalid lifecycle engine identity')
    require(type(engine['pid']) is int and engine['pid'] > 0 and type(engine['parentPid']) is int and engine['parentPid'] > 0
            and engine['pid'] != engine['parentPid'], 'Invalid lifecycle capture PID')
    require(all(type(engine[k]) is bool for k in ('isolated', 'pathEmpty', 'overridesAbsent')),
            'Invalid lifecycle isolation flag types')
    interval = value['captureInterval']; require(interval['clock'] == 'time.monotonic', 'Wrong capture clock')
    require(all(type(interval[k]) in (int, float) and math.isfinite(interval[k]) for k in ('started', 'finished'))
            and 0 <= interval['started'] < interval['finished'], 'Invalid capture interval')
    def snapshot(snapshot): validate_full_snapshot(snapshot, interval)
    def idle(snapshot, closed=False):
        validate_full_snapshot(snapshot, interval)
        require(snapshot['pending'] == 0 and snapshot['dispatcher_alive'] is False, 'Submission leases/dispatcher were not released')
        if closed: require(snapshot['state'] == 'closed' and not snapshot['worker_alive'], 'Instance not closed/reaped')
    def recover(record):
        idle(record['afterRecovery'])
        result = record['recoveryResult']; request = {'schema': 'py-elk-layout-request/v1', 'constructor': {}, 'layoutArguments': {}, 'graph': small_graph()}
        policy = {'profile': 'basic-flat-orthogonal', 'direction': 'RIGHT', 'padding': {'top': 12, 'right': 12, 'bottom': 12, 'left': 12},
                  'nodeNode': 20, 'betweenLayers': 20, 'forwardEdges': True, 'rankSeparation': 'default-layered-components-v2', 'layerFrame': 'independent-components-v1'}
        require(geometry(request, {'outcome': 'returned', 'result': result}, policy)['passed'], 'Recovery graph geometry failed')
        trace = record['recoveryTrace']
        require(type(trace) is list and [x['processor'] for x in trace] == list(NATIVE_PROCESSORS) and
                all(type(x['index']) is int and x['index'] == i and x['outcome'] == 'returned' for i, x in enumerate(trace)), 'Recovery did not execute the real complete phase chain')
    registry = value['registry']
    metadata_expected = load(ROOT/'tests/fixtures/suites/full-native-core/metadata-expected.json')['expectedQueries']
    exact(registry['default'], metadata_expected['default'], 'Registry contract differs')
    expected_aliases = [['layered'], ['org.eclipse.elk.layered'], ['layered', 'org.eclipse.elk.layered', 'layered']]
    require(len(registry['aliases']) == 3, 'Alias denominator differs')
    for row, aliases in zip(registry['aliases'], expected_aliases):
        exact(row['constructor'], {'algorithms': aliases}, 'Original aliases differ')
        require(row['constructorBeforeSha256'] == row['constructorAfterSha256'] == fingerprint(row['constructor']), 'Alias caller input mutated')
        mode = 'algorithmsEmpty' if aliases == ['org.eclipse.elk.layered'] else 'layered'
        exact(row['queries'], metadata_expected[mode], 'Actual provider registration/deduplication differs')
    error(registry['workerUrlError'], 'UnsupportedWorkerError', 'UNSUPPORTED_WORKER', '/constructor/workerUrl', 'JavaScript worker construction is unavailable in the native host')
    closed_trace = registry['closedTrace']; trace = closed_trace['before']
    require(type(trace) is list and [x['processor'] for x in trace] == list(NATIVE_PROCESSORS)
            and all(x['outcome'] == 'returned' for x in trace), 'Close had no previously published successful trace')
    exact(closed_trace['after'], [], 'Close did not clear previously published trace'); idle(closed_trace['closedSnapshot'], True)
    capacity = value['capacity']; require(len(capacity['valid']) == 2 and len(capacity['invalid']) == 3, 'Capacity denominator differs')
    for row, maximum in zip(capacity['valid'], (1, 64)):
        require(type(row['maxPending']) is int and row['maxPending'] == maximum, 'Capacity bound differs'); idle(row['before']); idle(row['closed'], True)
    for row, maximum in zip(capacity['invalid'], (0, 65, True)):
        require(type(row['value']) is type(maximum) and row['value'] == maximum, 'Invalid capacity input differs')
        error(row['error'], 'OptionValidationError', 'INVALID_OPTION_VALUE', '/max_pending', 'Expected an integer from 1 to 64')
    running = value['runningTimeout']; require(running['inputBeforeSha256'] == running['inputAfterSha256'] == fingerprint(cpu_graph()), 'Running timeout changed input')
    require(running['calibration']['timeout'] is None and running['calibration']['outcome'] == 'returned', 'CPU deadline calibration was not a real success')
    for attempt in [running['calibration'], *running['attempts']]:
        idle(attempt['after'])
        require(type(attempt['submissionCalledAt']) in (int, float) and type(attempt['finishedAt']) in (int, float)
                and interval['started'] <= attempt['submissionCalledAt'] <= attempt['finishedAt'] <= interval['finished'], 'Attempt clocks contradict capture')
        job = attempt['after']['jobs'][-1]
        events = attempt['phaseEvents']; stamps = [event['observedAt'] for event in events]
        require(all(finite(stamp) for stamp in stamps) and all(a < b for a, b in zip(stamps, stamps[1:])), 'CPU observations reordered or untyped')
        indices = []
        for event in attempt['phaseEvents']:
            snapshot(event['snapshot']); require(interval['started'] <= event['observedAt'] <= interval['finished'], 'Phase observation outside capture')
            observed = event['snapshot']['jobs'][-1]
            require(observed['state'] == 'running' and observed['pid'] == job['pid'] and event['snapshot']['worker_alive'] is True
                    and observed['job_id'] == job['job_id'], 'CPU observation does not belong to actual running timeout worker')
            require(job['started_at'] <= event['observedAt'] <= job['finished_at'], 'CPU event outside actual worker lifetime')
            require(finite(event['cpuSeconds']) and event['cpuSeconds'] >= 0, 'Invalid independently sampled OS CPU time')
            indices.append(observed['progress']['index'])
        require(indices == [0] * len(indices), 'Coordinator entry observations have invented phase indices')
        require(all(a['cpuSeconds'] < b['cpuSeconds'] for a, b in zip(events, events[1:])), 'OS CPU observations did not increase')
        require(attempt['submissionCalledAt'] <= job['submitted_at'] <= job['finished_at'] <= attempt['finishedAt'], 'Attempt clock excludes actual submission/lifetime')
        if attempt['pidBefore'] is not None: os_pid(attempt['pidBefore'], True)
        if attempt['pidAfter'] is not None: os_pid(attempt['pidAfter'], attempt['outcome'] == 'returned')
        if attempt['timeout'] is not None:
            require(type(attempt['timeout']) in (int, float) and math.isfinite(attempt['timeout']) and attempt['timeout'] > 0, 'Invalid actual total timeout')
    ordinal = running['qualifiedAttempt']; require(type(ordinal) is int and 0 <= ordinal < len(running['attempts']), 'Qualified deadline attempt missing')
    attempt = running['attempts'][ordinal]; require(_qualified(attempt), 'Timeout did not observe genuine running algorithm CPU')
    error(attempt['error'], 'ExecutionTimeoutError', 'EXECUTION_TIMEOUT', '', 'The layout submission deadline expired')
    job = attempt['after']['jobs'][-1]
    require(job['state'] == 'failed' and job['finished_at'] >= job['submitted_at']+attempt['timeout'] and job['progress'] is not None, 'Timeout did not follow the actual total deadline')
    require(attempt['outcome'] == 'threw' and all(event['observedAt'] < job['submitted_at']+attempt['timeout'] for event in attempt['phaseEvents']), 'CPU was not observed before submission deadline')
    require(attempt['pidBefore']['pid'] == attempt['pidAfter']['pid'] == job['pid'] and attempt['pidBefore']['alive'] is True and attempt['pidAfter']['alive'] is False, 'Running timeout did not stop the actual observed PID')
    recover(running)
    queued = value['queuedTimeout']; require(queued['fixture'] == 'private-busy-host-control', 'Queue fixture role differs')
    for key in ('running', 'queued', 'afterQueuedTimeout'): snapshot(queued[key])
    require(queued['queued']['pending'] == 2 and len(queued['queued']['queued']) == 1, 'No actual queued submission')
    queued_id = queued['queued']['queued'][0]; job = next(j for j in queued['afterQueuedTimeout']['jobs'] if j['job_id'] == queued_id)
    require(job['state'] == 'failed' and job['pid'] is None and job['started_at'] is None and job['reaped'] is True, 'Queued deadline spawned or did not expire')
    require(queued['afterQueuedTimeout']['pending'] == 1 and queued['afterQueuedTimeout']['worker_alive'] is True, 'Queued deadline stopped the other worker')
    error(queued['queuedError'], 'ExecutionTimeoutError', 'EXECUTION_TIMEOUT', '', 'The layout submission deadline expired'); idle(queued['afterCancel']); recover(queued)
    faults = value['faults']; require(set(faults) == {'unknownKind', 'wrongJob', 'badBody', 'internalImport', 'spawnFailure'}, 'Fault denominator differs')
    for kind, row in faults.items():
        idle(row['after']); recover(row)
        code = 'WORKER_PROTOCOL_ERROR' if kind in ('unknownKind', 'wrongJob', 'badBody') else 'WORKER_START_FAILED' if kind == 'spawnFailure' else 'WORKER_EXECUTION_FAILED'
        message = 'Invalid worker message' if code == 'WORKER_PROTOCOL_ERROR' else 'E09 deliberate spawn start failure' if kind == 'spawnFailure' else "No module named 'E09_DELIBERATELY_MISSING_MODULE'"
        error(row['error'], 'WorkerExecutionError', code, '', message)
        sent = row['sentMessages']; job = row['after']['jobs'][-1]
        if kind == 'unknownKind': exact(sent, [{'kind': 'E09_UNKNOWN', 'job_id': job['job_id']}], 'Unknown-kind actual message differs')
        elif kind == 'wrongJob':
            require(len(sent) == 1 and set(sent[0]) == {'kind','job_id','graph_tokens','trace','pid','process_time'}, 'Wrong-job envelope fields differ')
            require(type(sent[0]['job_id']) is int and sent[0]['job_id'] == job['job_id']+1 and sent[0]['kind'] == 'result' and sent[0]['graph_tokens'] == [['o',None],['e',None]] and sent[0]['trace'] == [], 'Wrong-job actual message differs')
            require(type(sent[0]['pid']) is int and sent[0]['pid'] == job['pid'] and finite(sent[0]['process_time']), 'Wrong-job process identity differs')
        elif kind == 'badBody': exact(sent, [{'kind': 'progress', 'job_id': job['job_id'], 'index': True}], 'Bad-body actual message differs')
        elif kind == 'spawnFailure': require(sent == [] and job['pid'] is None, 'Injected start failure unexpectedly spawned')
        else:
            require(len(sent) == 2, 'Actual import-failure message count differs')
            progress = sent[0]
            require(progress['kind'] == 'progress' and type(progress['job_id']) is int and progress['job_id'] == job['job_id'] and type(progress['index']) is int and progress['index'] == 0 and progress['processor'] == 'RecursiveLayoutEngine' and finite(progress['process_time']), 'Import failure lacked real coordinator entry')
            exact(sent[1], {'kind': 'error', 'job_id': job['job_id'], 'category': 'algorithm', 'type': 'ModuleNotFoundError', 'code': 'WORKER_EXECUTION_FAILED', 'path': '', 'message': message}, 'Actual internal import envelope differs')
    close = value['crossThreadClose']; require(close['fixture'] == 'private-busy-host-control', 'Close fixture role differs'); snapshot(close['runningAndQueued'])
    require(close['runningAndQueued']['pending'] == 2 and len(close['runningAndQueued']['queued']) == 1, 'Close lacked actual running and queued submissions')
    call = close['threadCall']; require(type(call['threadId']) is int and type(close['mainThreadId']) is int and call['threadId'] != close['mainThreadId'], 'Close did not run on another thread')
    require(interval['started'] <= call['startedAt'] <= call['finishedAt'] <= interval['finished'] and call['returnValue'] is None and close['secondReturnValue'] is None, 'Actual close return/time differs')
    idle(close['afterFirstClose'], True); idle(close['afterSecondClose'], True); exact(close['afterFirstClose'], close['afterSecondClose'], 'Second close changed closed state')
    require(len(close['errors']) == 2, 'Closed task error denominator differs')
    for record in close['errors']: error(record, 'ResourceClosedError', 'RESOURCE_CLOSED', '', 'The native instance is closed')
    require(close['pidBefore']['pid'] == close['pidAfter']['pid'] == close['runningAndQueued']['worker_pid'] and close['pidBefore']['alive'] is True and close['pidAfter']['alive'] is False, 'Other-thread close did not stop/reap the actual worker')
    os_pid(close['pidBefore'], True); os_pid(close['pidAfter'], False)
    return {'passed': True, 'status': 'FULL_HOST_LIFECYCLE_BODY_VALIDATED', 'privateFaults': 5, 'runtimeReexecuted': False,
            'cpuEvidence': 'independent OS GetProcessTimes/proc samples; one real coordinator progress entry', 'persistentWorker': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--development', action='store_true', help='Explicitly capture formal src instead of an isolated installed wheel')
    args = parser.parse_args()
    if args.development:
        if sys.flags.isolated: raise ValueError('Development mode requires an explicit nonisolated invocation')
        sys.path.insert(0, str(ROOT/'src'))
    args.capture.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = asyncio.run(capture_observation(args.capture.parent, installed=not args.development))
    except Exception as error:
        (args.capture.parent/'capture-failure.json').write_text(json.dumps(error_record(error)), encoding='utf8')
        raise
    with args.capture.open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2); stream.write('\n')
    validate_lifecycle_observation(value)


if __name__ == '__main__':
    main()
