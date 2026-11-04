"""Recompute E10 public-call measurements from original portable observations.

This is a pure verifier: no layout, old package, or platform process is launched.
Instrumented cost breakdowns are separate from these public-call statistics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e10
from validate_e09_coverage import decode_capture, expectations, semantic
from layout_checks import compare_observations

SUITE = 'tests/fixtures/suites/E10/benchmark.json'
COLLECTOR = 'tools/platform/benchmark_e10.py'
METRICS = ('publicElapsedSeconds', 'parentCpuSeconds', 'workerCpuSeconds',
           'parentPeakRssBytes', 'workerPeakRssBytes')


def reference_rows(root, definitions):
    rows = {r['definition']['id']: r for r in e10.load(root/'references/e09-coverage-validation.json')['cases']}
    fingerprints = expectations(root)
    old = None
    results = {}
    for definition in definitions:
        if definition.get('referenceSuite') == 'E06':
            if old is None: old = e10.load(root/definition['referenceReceipt'])
            row = next(r for r in old['objects'].values() if r['role'] == 'reference' and
                       r['requestSha256'] == definition['requestSha256'] and r['repetition'] == 0)
            raw = e10.raw64(old['observationBytesBase64'][row['observationSha256']])
            e10.require(e10.digest(raw) == row['observationSha256'], 'Original E06 reference bytes differ')
            policy = next(r for r in e10.load(root/'tests/fixtures/suites/E06/cases.json')['cases']
                          if r['id'] == definition['referenceCase'])
            results[definition['id']] = (policy, json.loads(raw))
        else:
            row = rows[definition['referenceCase']]
            raw = e10.raw64(row['requestBytesBase64']); request = json.loads(raw); request['_sha'] = e10.digest(raw)
            e10.require(e10.digest(raw) == definition['requestSha256'], 'Reference is not the same benchmark request')
            observation = decode_capture(row['captures'][0])
            e10.require(semantic(observation, request) == fingerprints[definition['referenceCase']],
                        'Original E09 reference semantics differ')
            results[definition['id']] = (row['definition'], observation)
    return results


def validate(value, root=ROOT):
    root = Path(root)
    try:
        e10.require(value['schema'] == 'py-elk-e10-benchmark-run/v1' and value['fullValidation'] is False,
                    'Unknown or full benchmark receipt')
        suite = e10.load(root/SUITE); definitions = suite['cases']
        e10.require(len(definitions) == 3 and suite['warmups'] == value['warmupsPerCase'] == 1 and
                    suite['samples'] == value['samplesPerCase'] == 5, 'Fixed benchmark denominator differs')
        e10.require(value['suiteSha256'] == e10.sha256(root/SUITE), 'Benchmark suite bytes differ')
        expected_slots = [(d['id'], ordinal) for d in definitions for ordinal in range(6)]
        e10.require([(c['caseId'], c['sample']) for c in value['captures']] == expected_slots,
                    'Expected three cases with one warmup and five samples in fixed order')
        dependencies = {name: e10.sha256(root/name) for name in
                        (COLLECTOR, 'scripts/verify_installed_wheel.py', SUITE)}
        source = e10.path(value['actualSourceRoot']); python = e10.path(value['candidatePython'])
        wheel = e10.path(value['wheel']); references = reference_rows(root, definitions)
        grouped = {d['id']: [] for d in definitions}; pids = []; previous_finish = None
        for row in value['captures']:
            definition = next(d for d in definitions if d['id'] == row['caseId'])
            e10.require(type(row['sample']) is int and row['warmup'] is (row['sample'] == 0), 'Warmup/sample role differs')
            command = e10.check_command(row); cwd = e10.path(command['cwd'])
            e10.exact(command['environmentPolicy'], {'pathEmpty':True, 'overridesAbsent':True},
                      'Recorded public driver environment policy differs')
            e10.require(not cwd.is_relative_to(source), 'Benchmark ran inside source checkout')
            expected_argv = [str(python), '-I', str(source/COLLECTOR), '--sample', '--wheel', str(wheel),
                             '--request', str(source/Path(SUITE).parent.as_posix()/definition['request']),
                             '--out', command['argv'][-1]]
            e10.exact(command['argv'], expected_argv, 'Actual isolated benchmark command differs')
            e10.require(e10.path(command['argv'][-1]).is_relative_to(cwd), 'Observation path escapes actual cwd')
            raw = e10.raw64(row['observationBytesBase64'])
            e10.require(e10.digest(raw) == row['observationSha256'], 'Original benchmark raw bytes differ')
            observation = e10.embedded_json(raw); engine = observation['engine']; installed = observation['installed']
            e10.require(observation['schema'] == 'py-elk-e10-benchmark-observation/v1' and
                        observation['mode'] == 'public' and observation['fullValidation'] is False,
                        'Instrumented or unknown observation substituted for public sample')
            e10.exact(observation['executionDependencies'], dependencies, 'Public capture dependencies changed')
            e10.exact(observation['definition'], definition, 'Benchmark case definition differs')
            e10.require(e10.path(engine['executable']) == python and engine['platform']['system'] == 'Linux' and
                        engine['isolated'] is True and engine['pathEmpty'] is True and engine['overridesAbsent'] is True,
                        'Actual benchmark interpreter/environment differs')
            e10.require(engine['python'] == installed['python'] and engine['version'] == installed['version'] and
                        installed['wheelSha256'] == value['wheelSha256'], 'Actual benchmark package differs')
            e10.validate_process_identity(engine, {'executionPid': command['pid']}, value['launcherPid'])
            e10.validate_installed_identity(installed, root, actual_source_root=value['actualSourceRoot'])
            request_raw = e10.raw64(observation['requestBytesBase64'])
            e10.require(request_raw == (root/Path(SUITE).parent/definition['request']).read_bytes() and
                        e10.digest(request_raw) == definition['requestSha256'] == observation['requestSha256'],
                        'Actual benchmark request bytes differ')
            request = json.loads(request_raw)
            for stem, key in (('input', 'graph'), ('constructor', 'constructor'), ('arguments', 'layoutArguments')):
                for suffix in ('Before', 'After'):
                    e10.exact(observation[stem+suffix], request[key], 'Benchmark mutated '+key)
            worker = observation['worker']; jobs = worker['snapshotAfterReturn']['jobs']
            e10.require(len(jobs) == 1 and jobs[0]['state'] == 'returned' and jobs[0]['reaped'] is True and
                        type(jobs[0]['exitcode']) is int and jobs[0]['exitcode'] == 0 and
                        type(worker['pid']) is int and worker['pid'] > 0 and
                        type(jobs[0]['pid']) is int and jobs[0]['pid'] == worker['pid'] and
                        worker['pid'] not in (engine['pid'],engine['parentPid']), 'Expected exactly one waited worker')
            for field, expected in {'state': 'closed', 'pending': 0, 'worker_alive': False,
                                    'dispatcher_alive': False, 'worker_pid': None}.items():
                e10.exact(worker['closedSnapshot'][field], expected, 'Benchmark did not release '+field)
            tracker = worker['resourceTrackerPid']
            e10.require(tracker is None and worker['resourceTrackerStillAlive'] is False or
                        type(tracker) is int and tracker > 0 and tracker != worker['pid'] and
                        worker['resourceTrackerStillAlive'] is True, 'Waited tracker could contaminate child resource usage')
            usage = observation['usage']; a, b = usage['selfBefore'], usage['selfAfter']
            c, d = usage['childrenBefore'], usage['childrenAfter']
            e10.require(usage['method'] == 'resource.getrusage' and all(c[k] == 0 for k in ('ru_utime', 'ru_stime', 'ru_maxrss')),
                        'A reused driver cannot attribute cumulative child usage to this worker')
            e10.require(all(e10.finite(v[k]) and v[k] >= 0 for v in (a,b,c,d)
                            for k in ('ru_utime', 'ru_stime', 'ru_maxrss')), 'Invalid raw OS usage values')
            window = observation['publicWindow']; start, finish = window['startNs'], window['finishNs']
            e10.require(window['clock'] == 'time.perf_counter_ns' and type(start) is int and type(finish) is int and
                        0 < start < finish and (previous_finish is None or previous_finish <= start),
                        'Public samples overlap or have invalid monotonic clocks')
            previous_finish = finish
            metrics = {'publicElapsedSeconds': (finish-start)/1e9,
                       'parentCpuSeconds': b['ru_utime']+b['ru_stime']-a['ru_utime']-a['ru_stime'],
                       'workerCpuSeconds': d['ru_utime']+d['ru_stime'],
                       'parentPeakRssBytes': b['ru_maxrss']*1024, 'workerPeakRssBytes': d['ru_maxrss']*1024}
            e10.require(all(e10.finite(v) and v >= 0 for v in metrics.values()) and metrics['workerCpuSeconds'] > 0 and
                        metrics['workerPeakRssBytes'] > 0, 'No positive actual worker resource observation')
            for key, expected in metrics.items(): e10.exact(observation['metrics'][key], expected, 'Recomputed OS metric differs: '+key)
            e10.require(observation['metrics']['rssSourceUnit'] == 'KiB' and
                        observation['metrics']['rssBytesMultiplier'] == 1024, 'RSS unit conversion differs')
            # Comparison view only: original raw observation remains unchanged.
            candidate = {k: observation[k] for k in ('inputBefore','inputAfter','constructorBefore','constructorAfter',
                                                    'argumentsBefore','argumentsAfter','result','requestSha256')}
            candidate.update(schema='py-elk-layout-observation/v1', engine=engine,
                             outcome='returned', termination={'outcome':'returned'})
            policy, reference = references[definition['id']]
            comparison = compare_observations(reference, candidate, profile='native-basic-layered-v1', request=request_raw)
            e10.require(comparison['passed'], 'Benchmark public coordinates differ from original reference')
            e10.require(e10.geometry(request, candidate, policy['geometry'])['passed'], 'Benchmark geometry failed')
            e10.exact(observation['traceSummary'], {'phaseCount':len(e10.NATIVE_PROCESSORS),
                       'processors':list(e10.NATIVE_PROCESSORS), 'outcomes':['returned']*len(e10.NATIVE_PROCESSORS)},
                       'Benchmark did not execute the expected native phases')
            pids.append(engine['pid'])
            if not row['warmup']: grouped[row['caseId']].append(metrics)
        e10.require(len(set(pids)) == 18, 'Benchmark driver process identities repeat')
        summary = {}
        for identifier, samples in grouped.items():
            summary[identifier] = {key: {'minimum':min(r[key] for r in samples),
                'median':statistics.median(r[key] for r in samples),
                'p95NearestRank':sorted(r[key] for r in samples)[-1],
                'maximum':max(r[key] for r in samples)} for key in METRICS}
        return {'passed':True,'errors':[],'captures':18,'warmups':3,'measuredSamples':15,'statistics':summary,
                'p95Method':'nearest rank ceil(0.95*5)=5; small sample p95 equals maximum',
                'fullValidation':False,'runtimeReexecuted':False,'historicalExecutionAuthenticated':False}
    except (ValueError,KeyError,TypeError,AttributeError,OSError,IndexError,OverflowError,StopIteration) as error:
        return {'passed':False,'errors':[str(error)],'fullValidation':False,'runtimeReexecuted':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('receipt',type=Path)
    parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    value=validate(e10.load(args.receipt));value.update(receiptSha256=e10.sha256(args.receipt),
        verifierSha256=e10.sha256(Path(__file__)), platformVerifierSha256=e10.sha256(Path(e10.__file__)))
    from layout_checks import write
    write(args.out,value);print(json.dumps(value,ensure_ascii=False));raise SystemExit(0 if value['passed'] else 1)


if __name__=='__main__': main()
