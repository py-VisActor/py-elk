"""Bounded public-call measurements in fresh Linux drivers, no full checks.

The OS child high-water RSS is valid because each fresh driver waits for only
one real layout worker. It is not a sampled RSS, allocation delta or tree sum.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = {'PYTHONPATH', 'PYTHONHOME', 'NODE_OPTIONS', 'NODE_PATH'}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def rusage(who):
    import resource
    value = resource.getrusage(who)
    return {name: getattr(value, name) for name in ('ru_utime', 'ru_stime', 'ru_maxrss', 'ru_ixrss', 'ru_idrss',
            'ru_isrss', 'ru_minflt', 'ru_majflt', 'ru_nswap', 'ru_inblock', 'ru_oublock', 'ru_msgsnd', 'ru_msgrcv',
            'ru_nsignals', 'ru_nvcsw', 'ru_nivcsw')}


def usage_metrics(before_self, after_self, before_children, after_children, start, finish):
    if any(before_children[k] != 0 for k in ('ru_utime', 'ru_stime', 'ru_maxrss')):
        raise ValueError('Worker measurements require a fresh driver with no previously waited children')
    if finish < start: raise ValueError('Public monotonic interval reversed')
    child_cpu = after_children['ru_utime']+after_children['ru_stime']
    parent_cpu = after_self['ru_utime']+after_self['ru_stime']-before_self['ru_utime']-before_self['ru_stime']
    if child_cpu <= 0 or after_children['ru_maxrss'] <= 0 or parent_cpu < 0:
        raise ValueError('OS usage did not establish positive real worker measurements')
    return {'publicElapsedSeconds': (finish-start)/1_000_000_000,
            'parentCpuSeconds': parent_cpu, 'workerCpuSeconds': child_cpu,
            'parentPeakRssBytes': after_self['ru_maxrss']*1024,
            'workerPeakRssBytes': after_children['ru_maxrss']*1024,
            'rssSourceUnit': 'KiB', 'rssBytesMultiplier': 1024,
            'peakScope': 'separate process high-water RSS, never summed or subtracted'}


async def sample(wheel, request_path):
    if sys.platform != 'linux': raise ValueError('This metric method is Linux getrusage; other benchmark platforms are unmeasured')
    if not sys.flags.isolated or os.environ.get('PATH') != '' or any(k.upper() in OVERRIDES for k in os.environ):
        raise ValueError('Sample requires -I, empty PATH and absent Python/Node overrides')
    import copy
    import importlib.util
    import platform
    import resource
    import pyelk
    module = Path(pyelk.__file__).resolve().parent
    if module.is_relative_to(ROOT/'src'): raise ValueError('Benchmark imported source instead of installed wheel')
    spec = importlib.util.spec_from_file_location('e10_verify_wheel', ROOT/'scripts/verify_installed_wheel.py')
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    installed = verifier.verify(wheel)
    raw = Path(request_path).read_bytes(); request = json.loads(raw)
    definitions = json.loads((ROOT/'tests/fixtures/suites/E10/benchmark.json').read_text())
    definition = next(x for x in definitions['cases'] if x['requestSha256'] == hashlib.sha256(raw).hexdigest())
    graph, constructor, arguments = copy.deepcopy(request['graph']), copy.deepcopy(request['constructor']), copy.deepcopy(request['layoutArguments'])
    engine = {'name': 'pyelk', 'version': pyelk.__version__, 'python': sys.version, 'versionInfo': list(sys.version_info[:3]),
              'executable': sys.executable, 'prefix': sys.prefix, 'basePrefix': sys.base_prefix,
              'pid': os.getpid(), 'parentPid': os.getppid(), 'isolated': bool(sys.flags.isolated),
              'modulePath': str(module), 'platform': {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()},
              'cpuCount': os.cpu_count(), 'affinity': sorted(os.sched_getaffinity(0)), 'loadBefore': list(os.getloadavg()),
              'pathEmpty': True, 'overridesAbsent': True}
    instance = pyelk.ELK(constructor, max_pending=1)
    before_self, before_children = rusage(resource.RUSAGE_SELF), rusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter_ns()
    try:
        result = await instance.layout(graph, arguments)
        finish = time.perf_counter_ns()
        after_self, after_children = rusage(resource.RUSAGE_SELF), rusage(resource.RUSAGE_CHILDREN)
        snapshot = instance._controller.snapshot()
        trace = instance.last_trace
    finally:
        instance.terminateWorker()
    closed = instance._controller.snapshot()
    if len(snapshot['jobs']) != 1 or snapshot['jobs'][0]['state'] != 'returned' or not snapshot['jobs'][0]['reaped']:
        raise ValueError('Sample did not wait for exactly one real layout worker')
    if graph != request['graph'] or constructor != request['constructor'] or arguments != request['layoutArguments']:
        raise ValueError('Public benchmark mutated caller inputs')
    from multiprocessing import resource_tracker
    tracker = getattr(resource_tracker._resource_tracker, '_pid', None)
    tracker_alive = False
    if tracker is not None:
        try: os.kill(tracker, 0); tracker_alive = True
        except ProcessLookupError: pass
    if tracker == snapshot['jobs'][0]['pid'] or tracker is not None and not tracker_alive:
        raise ValueError('Another waited child could contaminate worker resource measurements')
    return {'schema': 'py-elk-e10-benchmark-observation/v1', 'mode': 'public', 'fullValidation': False,
            'definition': definition, 'engine': engine, 'installed': installed,
            'executionDependencies': {'tools/platform/benchmark_e10.py': sha(__file__),
                                     'scripts/verify_installed_wheel.py': sha(ROOT/'scripts/verify_installed_wheel.py'),
                                     'tests/fixtures/suites/E10/benchmark.json': sha(ROOT/'tests/fixtures/suites/E10/benchmark.json')},
            'requestBytesBase64': base64.b64encode(raw).decode(), 'requestSha256': hashlib.sha256(raw).hexdigest(),
            'inputBefore': request['graph'], 'inputAfter': graph, 'constructorBefore': request['constructor'], 'constructorAfter': constructor,
            'argumentsBefore': request['layoutArguments'], 'argumentsAfter': arguments, 'result': result,
            'publicWindow': {'clock': 'time.perf_counter_ns', 'startNs': start, 'finishNs': finish},
            'usage': {'method': 'resource.getrusage', 'selfBefore': before_self, 'selfAfter': after_self,
                      'childrenBefore': before_children, 'childrenAfter': after_children},
            'metrics': usage_metrics(before_self, after_self, before_children, after_children, start, finish),
            'worker': {'pid': snapshot['jobs'][0]['pid'], 'snapshotAfterReturn': snapshot, 'closedSnapshot': closed,
                       'resourceTrackerPid': tracker, 'resourceTrackerStillAlive': tracker_alive,
                       'trackerExcludedReason': 'RUSAGE_CHILDREN counts waited children; the separate live tracker has not been waited'},
            'traceSummary': {'phaseCount': len(trace), 'processors': [x['processor'] for x in trace], 'outcomes': [x['outcome'] for x in trace]},
            'loadAfter': list(os.getloadavg()),
            'limitations': ['Public call includes spawn/IPC and trace return; constructor and package verification precede its timer.',
                           'Parent RSS is driver lifetime high-water through return, including setup. Worker RSS is its process lifetime high-water.',
                           'No concurrent tree-memory peak, hard memory/CPU quota, or ELK executionTime-as-seconds claim.']}


def collect(python, wheel, suite, out):
    from linux_e10 import run_command
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    definitions = json.loads(Path(suite).read_text()); rows = []
    for definition in definitions['cases']:
        for ordinal in range(definitions['warmups']+definitions['samples']):
            folder = out/definition['id']/str(ordinal); folder.mkdir(parents=True)
            observed = folder/'observation.json'
            command = run_command([str(python), '-I', str(Path(__file__).resolve()), '--sample', '--wheel', str(wheel),
                                   '--request', str(Path(suite).parent/definition['request']), '--out', str(observed)],
                                  folder/'command', cwd=out, runtime=True)
            if command['command']['exitCode'] != 0 or command['command']['timedOut']:
                raise ValueError('Benchmark sample failed; original command preserved')
            raw = observed.read_bytes()
            rows.append({'caseId': definition['id'], 'sample': ordinal, 'warmup': ordinal < definitions['warmups'], **command,
                         'observationBytesBase64': base64.b64encode(raw).decode(), 'observationSha256': hashlib.sha256(raw).hexdigest()})
    record = {'schema': 'py-elk-e10-benchmark-run/v1', 'actualSourceRoot': str(ROOT), 'launcherPid': os.getpid(),
              'candidatePython': str(python), 'wheel': str(wheel), 'wheelSha256': sha(wheel), 'suiteSha256': sha(suite),
              'warmupsPerCase': definitions['warmups'], 'samplesPerCase': definitions['samples'], 'captures': rows,
              'sampling': 'sequential after platform matrix', 'fullValidation': False}
    save(out/'receipt.json', record); return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True); group.add_argument('--sample', action='store_true'); group.add_argument('--run', action='store_true')
    parser.add_argument('--wheel', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--request', type=Path); parser.add_argument('--python', type=Path)
    parser.add_argument('--suite', type=Path, default=ROOT/'tests/fixtures/suites/E10/benchmark.json'); args = parser.parse_args()
    if args.sample:
        if args.request is None: parser.error('--sample requires --request')
        import asyncio
        args.out.parent.mkdir(parents=True, exist_ok=True)
        save(args.out, asyncio.run(sample(args.wheel.absolute(), args.request.absolute())))
    else:
        if args.python is None: parser.error('--run requires --python')
        collect(args.python.absolute(), args.wheel.absolute(), args.suite.absolute(), args.out)


if __name__ == '__main__': main()
